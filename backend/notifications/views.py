from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """
    List user notifications.
    Supports ?unread=true filter.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        unread = self.request.query_params.get('unread')
        if unread and unread.lower() in ('true', '1'):
            qs = qs.filter(is_read=False)
        return qs


class NotificationMarkReadView(APIView):
    """
    Mark a specific notification as read.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(id=pk, user=request.user)
            notification.is_read = True
            notification.save(update_fields=['is_read', 'updated_at'])
            return Response({'status': 'marked_read', 'id': str(pk)})
        except Notification.DoesNotExist:
            return Response({'error': {'code': 'NOT_FOUND', 'message': 'Notification not found'}}, status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllReadView(APIView):
    """
    Mark all notifications for the current user as read.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all_marked_read', 'count': updated})


class NotificationUnreadCountView(APIView):
    """
    Get unread notification count for badge display.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})
