from django.core.management import call_command
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class DemoResetView(APIView):
    """
    1-click reset endpoint for hackathon demo.
    Restores the complete §16 dataset.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            call_command('seed_demo', reset=True)
            return Response({"status": "success", "message": "Demo dataset restored successfully (§16)."})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)
