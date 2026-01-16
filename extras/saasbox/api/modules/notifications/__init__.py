"""
Notifications module for FCM push notifications.

This module provides endpoints for:
- Push token registration and management
- Notification preferences
- Emergency broadcasts

See FCM_NOTIFICATION_PLAN.md for architecture details.
"""
from modules.notifications.routes import router

__all__ = ["router"]
