import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

interface StopPoint {
  sequence: number;
  stop_type: 'PICKUP' | 'AGGREGATION' | 'DELIVERY';
  location_name: string;
  latitude: number;
  longitude: number;
  quantity_kg?: number;
}

interface LeafletRouteMapProps {
  stops: StopPoint[];
  height?: string;
}

export const LeafletRouteMap: React.FC<LeafletRouteMapProps> = ({ stops, height = '400px' }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Destroy existing instance if any
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    // Default center around Theni / Cumbum (9.9457, 77.4779)
    const centerLat = stops.length > 0 ? stops[0].latitude : 9.9457;
    const centerLng = stops.length > 0 ? stops[0].longitude : 77.4779;

    const map = L.map(mapContainerRef.current).setView([centerLat, centerLng], 10);
    mapInstanceRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map);

    const latLngs: [number, number][] = [];

    // Add markers for each stop
    stops.forEach((stop, index) => {
      latLngs.push([stop.latitude, stop.longitude]);

      const isPickup = stop.stop_type === 'PICKUP';
      const isHub = stop.stop_type === 'AGGREGATION';
      const isDelivery = stop.stop_type === 'DELIVERY';

      const color = isPickup ? '#16a34a' : isHub ? '#2563eb' : '#d97706';
      const label = isPickup ? `Stop ${stop.sequence}: Pickup` : isHub ? 'Hub' : 'Delivery';

      const customIcon = L.divIcon({
        className: 'custom-map-pin',
        html: `
          <div style="
            background: ${color};
            color: #ffffff;
            font-weight: 800;
            font-size: 11px;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            border: 2px solid #ffffff;
          ">
            ${stop.sequence}
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([stop.latitude, stop.longitude], { icon: customIcon }).addTo(map);
      marker.bindPopup(`
        <div style="font-family: sans-serif; font-size: 12px;">
          <strong style="color: ${color};">${label}</strong><br/>
          <strong>${stop.location_name}</strong><br/>
          ${stop.quantity_kg ? `Quantity: ${stop.quantity_kg} kg` : ''}
        </div>
      `);
    });

    // Draw connecting polyline
    if (latLngs.length > 1) {
      const polyline = L.polyline(latLngs, {
        color: '#15803d',
        weight: 4,
        opacity: 0.8,
        dashArray: '8, 8',
      }).addTo(map);

      map.fitBounds(polyline.getBounds(), { padding: [40, 40] });
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [stops]);

  return (
    <div
      ref={mapContainerRef}
      style={{
        width: '100%',
        height,
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--slate-300)',
        boxShadow: 'var(--shadow-sm)',
        zIndex: 1,
      }}
    />
  );
};
