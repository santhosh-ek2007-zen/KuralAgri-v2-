"""
Logistics domain services implementing D3 Produce Destination & Logistics Engine.
"""
from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.utils import timezone
from datetime import timedelta

from matching.models import Lot, LotContribution
from users.models import BuyerProfile
from logistics.models import (
    Vehicle,
    Route,
    RouteStop,
    DestinationCandidate,
    LogisticsCostBreakdown,
    LogisticsRateCard
)
from engine.economics import (
    ContributorPickupInput,
    DestinationCandidateInput,
    calculate_logistics_cost,
    evaluate_and_rank_destinations
)
from engine.routing import RouteNode, solve_cvrp_route, haversine_km


class LogisticsCostService:
    @staticmethod
    def calculate_cost_for_lot(lot: Lot, destination_buyer: Optional[BuyerProfile] = None) -> LogisticsCostBreakdown:
        rate_card = LogisticsRateCard.objects.filter(is_active=True).first()
        collection_rate = rate_card.collection_rate_per_kg_km if rate_card else Decimal('1.20')
        handling_fee = rate_card.handling_fee_per_kg if rate_card else Decimal('0.30')

        contributions = lot.contributions.all().select_related('farmer')
        pickup_inputs = []

        for c in contributions:
            dist = Decimal('5.00')  # Default 5 km collection radius
            pickup_inputs.append(ContributorPickupInput(
                contributor_id=str(c.id),
                quantity_kg=c.committed_quantity_kg,
                collection_distance_km=dist,
                self_delivery=c.listing.self_delivery if hasattr(c, 'listing') and c.listing else False
            ))

        trunk_distance = Decimal('20.00')  # Default Theni destination 20 km
        if destination_buyer:
            hub_lat = float(lot.aggregation_point.latitude) if lot.aggregation_point else 9.9457
            hub_lng = float(lot.aggregation_point.longitude) if lot.aggregation_point else 77.4779
            d = haversine_km(hub_lat, hub_lng, float(destination_buyer.latitude), float(destination_buyer.longitude))
            trunk_distance = Decimal(str(d))

        res = calculate_logistics_cost(
            lot_quantity_kg=lot.total_quantity_kg,
            trunk_distance_km=trunk_distance,
            contributors=pickup_inputs,
            collection_rate_per_kg_km=collection_rate,
            handling_fee_per_kg=handling_fee
        )

        breakdown, _ = LogisticsCostBreakdown.objects.update_or_create(
            lot=lot,
            defaults={
                'collection_cost': res.collection_cost,
                'handling_cost': res.handling_cost,
                'transport_cost': res.transport_cost,
                'urgency_cost': res.urgency_cost,
                'total_logistics_cost': res.total_logistics_cost,
                'direct_cost_comparison': res.total_logistics_cost * Decimal('1.15'),
                'consolidation_saving': res.total_logistics_cost * Decimal('0.15')
            }
        )
        return breakdown


class DestinationService:
    @staticmethod
    def evaluate_candidates(lot: Lot) -> List[DestinationCandidate]:
        # Delete old candidates
        DestinationCandidate.objects.filter(lot=lot).delete()

        buyers = BuyerProfile.objects.all()
        hub_lat = float(lot.aggregation_point.latitude) if lot.aggregation_point else 9.9457
        hub_lng = float(lot.aggregation_point.longitude) if lot.aggregation_point else 77.4779

        candidate_inputs = []
        for b in buyers:
            dist = haversine_km(hub_lat, hub_lng, float(b.latitude), float(b.longitude))
            candidate_inputs.append(DestinationCandidateInput(
                destination_id=str(b.id),
                buyer_name=b.organisation,
                channel=b.buyer_type,
                accepted_grades=b.accepted_grades or ['A'],
                daily_capacity_kg=b.daily_capacity_kg,
                min_order_kg=Decimal('100.00'),
                gross_price_per_kg=Decimal('35.00') if b.buyer_type == 'PREMIUM' else (Decimal('22.00') if b.buyer_type == 'SECONDARY' else Decimal('14.00')),
                road_distance_km=Decimal(str(dist))
            ))

        pickup_inputs = [
            ContributorPickupInput(
                contributor_id=str(c.id),
                quantity_kg=c.committed_quantity_kg,
                collection_distance_km=Decimal('5.00')
            )
            for c in lot.contributions.all()
        ]

        evaluated = evaluate_and_rank_destinations(
            lot_quantity_kg=lot.total_quantity_kg,
            grade=lot.grade,
            remaining_shelf_life_hours=Decimal('10.00'),
            contributors=pickup_inputs,
            candidates=candidate_inputs
        )

        persisted = []
        for idx, ev in enumerate(evaluated):
            buyer_obj = BuyerProfile.objects.get(id=ev.destination_id)
            obj = DestinationCandidate.objects.create(
                lot=lot,
                buyer=buyer_obj,
                distance_km=ev.distance_km,
                travel_time_hours=ev.travel_time_hours,
                gross_price_per_kg=ev.gross_price_per_kg,
                logistics_cost_per_kg=ev.logistics_cost_per_kg,
                net_return_per_kg=ev.net_return_per_kg,
                is_feasible=ev.is_feasible,
                rejection_reason=ev.rejection_reason,
                is_selected=(idx == 0 and ev.is_feasible)
            )
            persisted.append(obj)

        return persisted


class RoutingService:
    @staticmethod
    def plan_route(lot: Lot, vehicle: Optional[Vehicle] = None) -> Route:
        if not vehicle:
            # Pick smallest vehicle fitting capacity
            vehicle = Vehicle.objects.filter(
                capacity_kg__gte=lot.total_quantity_kg,
                is_available=True
            ).order_by('capacity_kg').first()

        if not vehicle:
            # Fallback vehicle
            vehicle = Vehicle.objects.create(
                registration_number=f"TN59AUTO{lot.lot_code[-4:]}",
                vehicle_type="MINI_TRUCK",
                capacity_kg=Decimal('1000.00'),
                cost_per_km=Decimal('18.00'),
                base_location="Theni"
            )

        depot = RouteNode(
            id="depot",
            name=f"{vehicle.base_location} Vehicle Base",
            latitude=9.9457,
            longitude=77.4779,
            demand_kg=0.0,
            node_type="BASE"
        )

        pickups = []
        for c in lot.contributions.all().select_related('farmer'):
            pickups.append(RouteNode(
                id=str(c.id),
                name=f"{c.farmer.user.full_name} ({c.farmer.village})",
                latitude=float(c.farmer.latitude),
                longitude=float(c.farmer.longitude),
                demand_kg=float(c.committed_quantity_kg),
                node_type="PICKUP"
            ))

        dest_buyer = lot.buyer_order.buyer if lot.buyer_order else None
        dest_lat = float(dest_buyer.latitude) if dest_buyer else 9.9457
        dest_lng = float(dest_buyer.longitude) if dest_buyer else 77.4779
        dest_name = dest_buyer.organisation if dest_buyer else "Delivery Point"

        delivery = RouteNode(
            id="delivery",
            name=dest_name,
            latitude=dest_lat,
            longitude=dest_lng,
            demand_kg=float(lot.total_quantity_kg),
            node_type="DELIVERY"
        )

        sol = solve_cvrp_route(
            depot_node=depot,
            pickup_nodes=pickups,
            delivery_node=delivery,
            vehicle_capacity_kg=float(vehicle.capacity_kg),
            vehicle_id=str(vehicle.id)
        )

        now = timezone.now()
        route = Route.objects.create(
            lot=lot,
            vehicle=vehicle,
            total_distance_km=Decimal(str(sol.total_distance_km)),
            total_duration_hours=Decimal(str(sol.total_duration_hours)),
            total_cost=Decimal(str(sol.total_distance_km)) * vehicle.cost_per_km,
            solver=sol.solver,
            eta=now + timedelta(hours=sol.total_duration_hours),
            meets_deadline=True,
            status='PLANNED'
        )

        for stop_dict in sol.stop_sequence:
            cid = stop_dict.get("contribution_id")
            contrib_obj = LotContribution.objects.filter(id=cid).first() if cid else None
            RouteStop.objects.create(
                route=route,
                sequence=stop_dict["sequence"],
                stop_type=stop_dict["stop_type"],
                contribution=contrib_obj,
                name=stop_dict["name"],
                latitude=Decimal(str(stop_dict["latitude"])),
                longitude=Decimal(str(stop_dict["longitude"])),
                quantity_kg=Decimal(str(stop_dict["quantity_kg"])),
                planned_eta=now + timedelta(hours=(stop_dict["cumulative_distance_km"] / 35.0))
            )

        return route
