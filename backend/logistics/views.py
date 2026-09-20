from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from common.permissions import ReadOnly, IsPlatformAdmin
from matching.models import Lot
from logistics.models import Route, DestinationCandidate, LogisticsCostBreakdown, Vehicle
from logistics.serializers import (
    RouteSerializer,
    DestinationCandidateSerializer,
    LogisticsCostBreakdownSerializer,
    VehicleSerializer
)
from logistics.services import RoutingService, DestinationService, LogisticsCostService
from common.audit import log_audit_event


class VehicleListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vehicles = Vehicle.objects.filter(is_available=True)
        serializer = VehicleSerializer(vehicles, many=True)
        return Response(serializer.data)


class RouteListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lot_id = request.query_params.get('lot_id')
        routes = Route.objects.all().select_related('vehicle', 'lot').prefetch_related('stops')
        if lot_id:
            routes = routes.filter(lot_id=lot_id)
        serializer = RouteSerializer(routes, many=True)
        return Response(serializer.data)

    def post(self, request):
        lot_id = request.data.get('lot_id')
        if not lot_id:
            return Response({"error": "lot_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        lot = get_object_or_404(Lot, id=lot_id)
        route = RoutingService.plan_route(lot)

        log_audit_event(
            user=request.user,
            action="ROUTE_PLANNED",
            entity_type="Route",
            entity_id=route.id,
            metadata={
                "lot_id": str(lot.id),
                "total_distance_km": float(route.total_distance_km),
                "total_duration_hours": float(route.total_duration_hours),
                "total_cost": float(route.total_cost)
            }
        )

        return Response(RouteSerializer(route).data, status=status.HTTP_201_CREATED)


class RouteDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        route = get_object_or_404(Route.objects.select_related('vehicle', 'lot').prefetch_related('stops'), id=pk)
        return Response(RouteSerializer(route).data)

    def patch(self, request, pk):
        route = get_object_or_404(Route, id=pk)
        new_status = request.data.get('status')
        valid_statuses = [s[0] for s in Route.STATUS_CHOICES]
        if new_status in valid_statuses:
            route.status = new_status
            route.save(update_fields=['status'])

            log_audit_event(
                user=request.user,
                action="ROUTE_STATUS_UPDATED",
                entity_type="Route",
                entity_id=route.id,
                metadata={"status": new_status}
            )

        return Response(RouteSerializer(route).data)


class DestinationCandidateListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lot_id = request.query_params.get('lot_id')
        if not lot_id:
            return Response({"error": "lot_id query param is required"}, status=status.HTTP_400_BAD_REQUEST)

        lot = get_object_or_404(Lot, id=lot_id)
        candidates = DestinationCandidate.objects.filter(lot=lot).select_related('buyer')
        if not candidates.exists():
            candidates = DestinationService.evaluate_candidates(lot)

        serializer = DestinationCandidateSerializer(candidates, many=True)
        return Response(serializer.data)

    def post(self, request):
        lot_id = request.data.get('lot_id')
        if not lot_id:
            return Response({"error": "lot_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        lot = get_object_or_404(Lot, id=lot_id)
        candidates = DestinationService.evaluate_candidates(lot)
        return Response(DestinationCandidateSerializer(candidates, many=True).data, status=status.HTTP_200_OK)


class LogisticsCostView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lot_id = request.query_params.get('lot_id')
        if not lot_id:
            return Response({"error": "lot_id query param is required"}, status=status.HTTP_400_BAD_REQUEST)

        lot = get_object_or_404(Lot, id=lot_id)
        try:
            breakdown = lot.cost_breakdown
        except LogisticsCostBreakdown.DoesNotExist:
            breakdown = LogisticsCostService.calculate_cost_for_lot(lot)

        return Response(LogisticsCostBreakdownSerializer(breakdown).data)
