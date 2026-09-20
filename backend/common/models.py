import uuid
from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model providing UUID primary key and automatic timestamps.
    Used by all domain models across KuralAgri.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class AuditLog(models.Model):
    """
    Immutable audit log tracking all critical state transitions and business events.
    Written directly by services across M1-M9.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_email = models.CharField(max_length=255, null=True, blank=True)
    user_role = models.CharField(max_length=50, null=True, blank=True)
    action = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=100, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp.isoformat()}] {self.action} on {self.entity_type}:{self.entity_id} by {self.user_email or 'system'}"
