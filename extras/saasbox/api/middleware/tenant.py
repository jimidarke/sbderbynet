"""
Multi-tenant middleware for setting organization context.
Uses PostgreSQL Row-Level Security (RLS) for data isolation.
"""
from typing import Callable

from fastapi import Request, Response
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import async_session_factory


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sets the tenant context for each request.
    Extracts org_id from the URL path and sets it as a PostgreSQL session variable.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with tenant context."""
        # Extract org_id from path if present
        # Expected URL patterns:
        # - /v1/orgs/{org_id}/...
        # - /v1/admin/... (no tenant context, system admin only)

        org_id = self._extract_org_id(request.url.path)

        if org_id:
            # Store org_id in request state for later use
            request.state.org_id = org_id
        else:
            request.state.org_id = None

        response = await call_next(request)
        return response

    def _extract_org_id(self, path: str) -> str | None:
        """
        Extract organization ID from URL path.

        Examples:
            /v1/orgs/org_abc123/events -> org_abc123
            /v1/orgs/org_abc123/events/evt_xyz/races -> org_abc123
            /v1/admin/stats -> None
            /v1/auth/me -> None
        """
        parts = path.strip("/").split("/")

        # Look for /orgs/{org_id} pattern
        try:
            orgs_index = parts.index("orgs")
            if len(parts) > orgs_index + 1:
                potential_org_id = parts[orgs_index + 1]
                # Validate it looks like an org_id
                if potential_org_id.startswith("org_"):
                    return potential_org_id
        except ValueError:
            pass

        return None


async def set_tenant_context(org_id: str) -> None:
    """
    Set the tenant context for the current database session.
    Call this within a route handler after validating the user has access.

    Usage:
        @router.get("/orgs/{org_id}/events")
        async def list_events(org_id: str, db: DBSession):
            await set_tenant_context(org_id)
            # All subsequent queries are now scoped to this org
            events = await db.execute(select(Event))
    """
    async with async_session_factory() as session:
        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, false)"),
            {"org_id": org_id}
        )


def get_tenant_policy_sql(table_name: str) -> str:
    """
    Generate SQL for creating RLS policy on a table.

    Args:
        table_name: Name of the table

    Returns:
        SQL statements to enable RLS and create policy
    """
    return f"""
-- Enable RLS on {table_name}
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation
-- Allows access when:
-- 1. Row's org_id matches current tenant context, OR
-- 2. No tenant context is set (for system admin queries)
CREATE POLICY tenant_isolation_{table_name} ON {table_name}
    USING (
        org_id = current_org_id()
        OR current_org_id() IS NULL
    );

-- Force RLS for table owner as well (security)
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;
"""


# Tables that need RLS policies (have org_id column)
TENANT_SCOPED_TABLES = [
    "organizations",  # Self-referential - users can only see their own orgs
    "organization_members",
    "events",
    "racer_classes",
    "racers",
    "rounds",
    "heats",
    "race_results",
    "polls",
    "poll_votes",
    "devices",
]


def generate_all_rls_policies() -> str:
    """Generate RLS policies for all tenant-scoped tables."""
    policies = []
    for table in TENANT_SCOPED_TABLES:
        policies.append(get_tenant_policy_sql(table))
    return "\n".join(policies)
