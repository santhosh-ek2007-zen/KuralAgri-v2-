"""
Audit logging service.
Creates immutable audit trail entries across all business events.
"""
import logging
from common.models import AuditLog

logger = logging.getLogger(__name__)


def log_audit_event(
    action: str,
    entity_type: str,
    entity_id: str,
    user=None,
    metadata: dict = None,
    ip_address: str = None
) -> AuditLog:
    """
    Log an immutable audit event to PostgreSQL.
    """
    try:
        user_id = None
        user_email = None
        user_role = None

        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            user_id = getattr(user, 'id', None)
            user_email = getattr(user, 'email', None)
            user_role = getattr(user, 'role', None)

        entry = AuditLog.objects.create(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            metadata=metadata or {},
            ip_address=ip_address
        )
        return entry
    except Exception as e:
        logger.error(f"Failed to record audit log for action={action}: {e}")
        return None
