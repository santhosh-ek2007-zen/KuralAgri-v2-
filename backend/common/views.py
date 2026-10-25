from django.core.management import call_command
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class DemoResetView(APIView):
    """
    1-click reset endpoint for hackathon demo.
    Restores the complete §16 dataset with 0 listings so all views
    start clean for live demoing the farmer listing -> buyer sourcing -> admin pipeline.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            call_command('seed_demo', reset=True, no_listings=True)
            from marketplace.models import Listing
            Listing.objects.all().delete()
            return Response({
                "status": "success",
                "message": "Demo reset complete! All listings cleared across Farmer, Buyer, and Admin views."
            })
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)

