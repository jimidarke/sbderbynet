"""
Firebase Authentication integration.
Verifies Firebase ID tokens and exchanges them for API JWTs.
"""
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import firebase_admin

# Initialize Firebase Admin SDK
_firebase_app: "firebase_admin.App | None" = None


def init_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    global _firebase_app

    if _firebase_app is not None:
        return

    import firebase_admin
    from firebase_admin import credentials
    from app.config import get_settings
    settings = get_settings()

    if settings.firebase_credentials_path:
        cred = credentials.Certificate(settings.firebase_credentials_path)
    else:
        # Use Application Default Credentials in cloud environments
        cred = credentials.ApplicationDefault()

    _firebase_app = firebase_admin.initialize_app(
        cred,
        options={"projectId": settings.firebase_project_id},
    )


async def verify_firebase_token(id_token: str) -> dict[str, Any]:
    """
    Verify a Firebase ID token and return the decoded claims.

    Args:
        id_token: The Firebase ID token from the client

    Returns:
        Decoded token claims containing user info:
        - uid: Firebase user ID
        - email: User's email
        - name: Display name (if set)
        - picture: Profile picture URL (if set)
        - email_verified: Whether email is verified
        - firebase.sign_in_provider: "google.com" for Google auth

    Raises:
        ValueError: If token is invalid, expired, or revoked
    """
    from firebase_admin import auth

    init_firebase()

    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(
            id_token,
            check_revoked=True,  # Check if token has been revoked
        )

        # Ensure it's a Google sign-in (for now, Gmail only)
        sign_in_provider = decoded_token.get("firebase", {}).get("sign_in_provider", "")
        if sign_in_provider != "google.com":
            raise ValueError(f"Invalid sign-in provider: {sign_in_provider}. Only Google sign-in is allowed.")

        # Ensure email is verified
        if not decoded_token.get("email_verified", False):
            raise ValueError("Email not verified")

        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture"),
            "email_verified": decoded_token.get("email_verified", False),
            "sign_in_provider": sign_in_provider,
        }

    except auth.InvalidIdTokenError as e:
        raise ValueError(f"Invalid ID token: {e}")
    except auth.ExpiredIdTokenError:
        raise ValueError("ID token has expired")
    except auth.RevokedIdTokenError:
        raise ValueError("ID token has been revoked")
    except auth.CertificateFetchError:
        raise ValueError("Failed to fetch Firebase certificates")
    except Exception as e:
        raise ValueError(f"Token verification failed: {e}")


async def get_firebase_user(uid: str) -> dict[str, Any] | None:
    """
    Get Firebase user record by UID.

    Args:
        uid: Firebase user ID

    Returns:
        User record or None if not found
    """
    from firebase_admin import auth

    init_firebase()

    try:
        user = auth.get_user(uid)
        return {
            "uid": user.uid,
            "email": user.email,
            "display_name": user.display_name,
            "photo_url": user.photo_url,
            "email_verified": user.email_verified,
            "disabled": user.disabled,
            "created_at": user.user_metadata.creation_timestamp,
            "last_sign_in": user.user_metadata.last_sign_in_timestamp,
        }
    except auth.UserNotFoundError:
        return None
    except Exception:
        return None


async def revoke_firebase_tokens(uid: str) -> bool:
    """
    Revoke all refresh tokens for a Firebase user.
    Use this when banning a user.

    Args:
        uid: Firebase user ID

    Returns:
        True if successful
    """
    from firebase_admin import auth

    init_firebase()

    try:
        auth.revoke_refresh_tokens(uid)
        return True
    except Exception:
        return False
