from django.db import models
from django.conf import settings
from common.models import BaseModel


class Notification(BaseModel):
    """
    In-app notifications for farmers, buyers, FPO admins, and platform admins.
    Created by domain services upon important state changes.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=64, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Notification({self.user_id}, '{self.title}', read={self.is_read})"
