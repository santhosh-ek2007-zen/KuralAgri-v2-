"""
Notification service for triggering in-app notifications.
Called synchronously by domain services across M3-M9.
"""
import logging
from .models import Notification

logger = logging.getLogger(__name__)


def send_notification(user, title: str, message: str, notification_type: str, metadata: dict = None) -> Notification:
    """
    Deliver an in-app notification to a user.
    Non-blocking on error so business logic never fails due to notification dispatch.
    """
    try:
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            metadata=metadata or {}
        )
    except Exception as e:
        logger.error(f"Failed to dispatch notification to user {getattr(user, 'id', None)}: {e}")
        return None
