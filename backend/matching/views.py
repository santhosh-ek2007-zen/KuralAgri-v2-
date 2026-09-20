from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from marketplace.models import BuyerOrder
from .models import Lot, LotContribution
from .serializers import LotSerializer
from .services import MatchingService, LotService
from common.permissions import IsBuyer, IsOwnerOrAdmin
from common.audit import log_audit_event


class MatchOrderView(APIView):
    """
    Evaluate available listings and match supply for a BuyerOrder.
    Returns matched contributors and shortfall decision.
    """
    permission_classes = [IsAuthenticated, IsBuyer]

    def post(self, request, pk):
        order = get_object_or_404(BuyerOrder, id=pk)
        match_result = MatchingService.match_supply_for_order(order)

        # Serialize output
        contributions_out = []
        for c in match_result["contributions"]:
            contributions_out.append({
                "listing_id": str(c["listing"].id),
                "farmer_name": c["listing"].farmer.user.full_name,
                "village": c["listing"].village,
                "distance_km": c["distance_km"],
                "allocated_kg": str(c["allocated_kg"]),
                "match_score": str(c["match_score"])
            })

        return Response({
            "order_id": str(order.id),
            "order_code": order.order_code,
            "target_quantity_kg": str(order.quantity_kg),
            "total_allocated_kg": str(match_result["total_allocated_kg"]),
            "shortfall_kg": str(match_result["shortfall_kg"]),
            "is_fulfilled": match_result["is_fulfilled"],
            "policy_decision": match_result["policy_decision"],
            "contributions": contributions_out
        })


class FormLotView(APIView):
    """
    Execute matching and form a PROPOSED Lot.
    """
    permission_classes = [IsAuthenticated, IsBuyer]

    def post(self, request, pk):
        order = get_object_or_404(BuyerOrder, id=pk)
        match_result = MatchingService.match_supply_for_order(order)

        if not match_result["contributions"]:
            return Response({
                "error": {
                    "code": "SHORTFALL_REJECTED",
                    "message": "No suitable active supply listings found to satisfy this requirement."
                }
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        lot = LotService.form_lot_from_match(order, match_result)
        return Response(LotSerializer(lot).data, status=status.HTTP_201_CREATED)


class LotListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LotSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Lot.objects.all().select_related('crop', 'buyer_order__buyer__user').prefetch_related('contributions__farmer__user')

        if not user.is_staff and user.role == 'BUYER':
            return qs.filter(buyer_order__buyer__user=user)
        elif not user.is_staff and user.role in ('FARMER', 'FPO'):
            return qs.filter(contributions__farmer__user=user).distinct()

        return qs


class LotDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LotSerializer
    queryset = Lot.objects.all().select_related('crop', 'buyer_order__buyer__user').prefetch_related('contributions__farmer__user')


class AcceptLotView(APIView):
    """
    Buyer accepts the proposed Lot price.
    Transitions status to ACCEPTED and validates price bounds [min_viable, ceiling].
    """
    permission_classes = [IsAuthenticated, IsBuyer]

    def post(self, request, pk):
        lot = get_object_or_404(Lot, id=pk)
        agreed_price = Decimal(str(request.data.get('agreed_price', lot.agreed_price_per_kg)))

        if agreed_price < lot.minimum_viable_price_per_kg:
            return Response({
                "error": {
                    "code": "PRICE_BELOW_MINIMUM_VIABLE",
                    "message": f"Agreed price ₹{agreed_price} cannot be below minimum viable lot price ₹{lot.minimum_viable_price_per_kg}."
                }
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        lot.agreed_price_per_kg = agreed_price
        lot.status = 'ACCEPTED'
        lot.save(update_fields=['agreed_price_per_kg', 'status'])

        log_audit_event(
            action="LOT_ACCEPTED",
            entity_type="Lot",
            entity_id=str(lot.id),
            user=request.user,
            metadata={
                "agreed_price": str(agreed_price),
                "total_quantity_kg": str(lot.total_quantity_kg)
            }
        )

        return Response(LotSerializer(lot).data)
