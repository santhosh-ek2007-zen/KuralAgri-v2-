import React, { useState, useEffect } from 'react';
import { api, Lot, PriceBreakdown, Listing } from '../api';
import { LeafletRouteMap } from './LeafletRouteMap';
import {
  TrendingUp,
  Truck,
  ShieldAlert,
  CheckCircle,
  Clock,
  DollarSign,
  Layers,
  ArrowRight,
  AlertTriangle,
  Play,
  RotateCcw,
  Scale
} from 'lucide-react';

interface AdminViewProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
}

export const AdminView: React.FC<AdminViewProps> = ({ currentTab, onTabChange }) => {
  const [lots, setLots] = useState<Lot[]>([]);
  const [selectedLot, setSelectedLot] = useState<Lot | null>(null);
  const [routePlan, setRoutePlan] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Quality check modal
  const [showQualityModal, setShowQualityModal] = useState(false);
  const [acceptedQty, setAcceptedQty] = useState('350');
  const [rejectedQty, setRejectedQty] = useState('150');
  const [rejectionReason, setRejectionReason] = useState('GRADE_MISMATCH');
  const [submittingCheck, setSubmittingCheck] = useState(false);

  // Recovery candidates
  const [candidates, setCandidates] = useState<any[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);
  const [recovering, setRecovering] = useState(false);
  const [recoverySuccess, setRecoverySuccess] = useState<string | null>(null);

  // Settlement execution
  const [settling, setSettling] = useState(false);
  const [settlementResult, setSettlementResult] = useState<any>(null);

  // Ledger entries
  const [ledgerEntries, setLedgerEntries] = useState<any[]>([]);

  // All farmer listings (admin monitoring)
  const [allListings, setAllListings] = useState<Listing[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [lotsRes, ledgerRes, listingsRes] = await Promise.all([
        api.getLots(),
        api.getLedgerEntries().catch(() => []),
        api.getAllListings().catch(() => [] as Listing[]),
      ]);
      setLots(lotsRes);
      setLedgerEntries(ledgerRes);
      setAllListings(listingsRes);
      if (lotsRes.length > 0 && !selectedLot) {
        setSelectedLot(lotsRes[0]);
      }
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePlanRoute = async (lotId: string) => {
    try {
      const res = await api.planRoute(lotId);
      setRoutePlan(res);
    } catch (err: any) {
      alert(`Route planning error: ${err.message}`);
    }
  };

  const handleEvaluateDestinations = async (lotId: string) => {
    try {
      const res = await api.evaluateDestinations(lotId);
      setCandidates(res);
      if (res.length > 0) setSelectedCandidate(res[0]);
    } catch (err: any) {
      alert(`Destination evaluation error: ${err.message}`);
    }
  };

  const handleSubmitQualityCheck = async () => {
    if (!selectedLot) return;
    try {
      setSubmittingCheck(true);
      await api.submitQualityCheck({
        lot_id: selectedLot.id,
        stage: 'HANDOVER',
        verified_grade: selectedLot.grade,
        verified_qty_kg: parseFloat(acceptedQty),
        notes: `Accepted ${acceptedQty}kg, rejected ${rejectedQty}kg (${rejectionReason})`,
      });
      setShowQualityModal(false);
      loadData();
      if (parseFloat(rejectedQty) > 0) {
        onTabChange('rejection_recovery');
        handleEvaluateDestinations(selectedLot.id);
      }
    } catch (err: any) {
      alert(`Quality check error: ${err.message}`);
    } finally {
      setSubmittingCheck(false);
    }
  };

  const handleExecuteRecovery = async () => {
    if (!selectedLot) return;
    try {
      setRecovering(true);
      const res = await api.recoverLot({
        original_lot_id: selectedLot.id,
        quantity_kg: parseFloat(rejectedQty) || 150,
        grade: 'B',
        remaining_shelf_life_hours: 6,
      });
      setRecoverySuccess(`Recovery outcome: ${res.outcome} for ${res.quantity_kg}kg produce. Recovered value: ₹${res.recovered_value}!`);
      loadData();
    } catch (err: any) {
      alert(`Recovery error: ${err.message}`);
    } finally {
      setRecovering(false);
    }
  };

  const handleExecuteSettlement = async (lotId: string) => {
    try {
      setSettling(true);
      const res = await api.settleLot(lotId);
      setSettlementResult(res);
      loadData();
    } catch (err: any) {
      alert(`Settlement error: ${err.message}`);
    } finally {
      setSettling(false);
    }
  };

  // Sample stops for interactive map
  const demoStops = [
    { sequence: 1, stop_type: 'PICKUP' as const, location_name: 'Cumbum (Ravi Kumar)', latitude: 9.7200, longitude: 77.2800, quantity_kg: 120 },
    { sequence: 2, stop_type: 'PICKUP' as const, location_name: 'Uthamapalayam (Meena Lakshmi)', latitude: 9.8050, longitude: 77.3400, quantity_kg: 150 },
    { sequence: 3, stop_type: 'PICKUP' as const, location_name: 'Bodinayakanur (Suresh Pandian)', latitude: 10.0104, longitude: 77.3507, quantity_kg: 80 },
    { sequence: 4, stop_type: 'PICKUP' as const, location_name: 'Chinnamanur (Karthik R)', latitude: 9.8398, longitude: 77.3827, quantity_kg: 150 },
    { sequence: 5, stop_type: 'AGGREGATION' as const, location_name: 'Cumbum Valley FPO Hub', latitude: 9.7200, longitude: 77.2800, quantity_kg: 500 },
    { sequence: 6, stop_type: 'DELIVERY' as const, location_name: 'Theni Fresh Mart (Buyer)', latitude: 9.9457, longitude: 77.4779, quantity_kg: 500 },
  ];

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
      
      {/* Admin KPI Header */}
      <div style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', color: 'var(--slate-900)' }}>
              Operations & Logistics Console
            </h1>
            <p style={{ fontSize: '0.85rem', color: 'var(--slate-500)' }}>
              Consolidated CVRP route optimization, quality gates, anti-waste recovery, and append-only ledger settlement.
            </p>
          </div>
          <span className="badge badge-info" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            System Status: Operational • All Rails Simulated
          </span>
        </div>

        {/* 5 KPI Metric Cards */}
        <div className="grid-4" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
          <div className="card" style={{ padding: '18px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase' }}>Lots Settled</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--slate-900)', marginTop: '4px' }} className="tabular">2 Lots</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--primary-700)', fontWeight: 600 }}>100% On-time delivery</div>
          </div>

          <div className="card" style={{ padding: '18px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase' }}>Gross Merch Value</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--slate-900)', marginTop: '4px' }} className="tabular">₹22,740</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>Total platform throughput</div>
          </div>

          <div className="card" style={{ padding: '18px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase' }}>Avg Farmer Uplift</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--primary-700)', marginTop: '4px' }} className="tabular">+27.0%</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>vs traditional mandi net</div>
          </div>

          <div className="card" style={{ padding: '18px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase' }}>Waste Diverted</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--amber-700)', marginTop: '4px' }} className="tabular">150 kg</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--amber-700)', fontWeight: 600 }}>Recovered to 2nd buyer</div>
          </div>

          <div className="card" style={{ padding: '18px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase' }}>Risk Reserve Balance</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--primary-800)', marginTop: '4px' }} className="tabular">₹25,000</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>Buffer for default write-off</div>
          </div>
        </div>
      </div>

      {/* ── Farmer Listings Monitor ──────────────────────────────────── */}
      {currentTab === 'admin_dashboard' && (
        <div className="card" style={{ padding: '24px', marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', color: 'var(--slate-900)' }}>🌾 Farmer Produce Listings</h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
                All listings across all statuses — monitor supply pipeline and shelf-life urgency.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span className="badge badge-neutral">{allListings.length} Total</span>
              <span className="badge badge-success">{allListings.filter(l => l.status === 'ACTIVE').length} Active</span>
              <span className="badge badge-warning">{allListings.filter(l => l.status === 'RESERVED').length} Reserved</span>
              <button className="btn btn-secondary btn-sm" onClick={loadData}>Refresh</button>
            </div>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--slate-500)' }}>Loading listings…</div>
          ) : allListings.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px', border: '1px dashed var(--slate-300)', borderRadius: 'var(--radius-md)', color: 'var(--slate-500)' }}>
              No farmer listings yet. Ask a farmer to list produce.
            </div>
          ) : (
            <div className="table-container" style={{ marginBottom: '0' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Farmer</th>
                    <th>Crop &amp; Grade</th>
                    <th>Qty (Avail / Total)</th>
                    <th>Location</th>
                    <th>Shelf Life</th>
                    <th>Floor Price</th>
                    <th>Status</th>
                    <th>Listed At</th>
                  </tr>
                </thead>
                <tbody>
                  {allListings.map((l) => {
                    const cropName = typeof l.crop === 'object' ? l.crop.name : l.crop;
                    const farmerName = l.farmer?.user?.full_name || 'Farmer';
                    const shelfHours = parseFloat(l.remaining_shelf_life_hours || '0');
                    const isExpiring = shelfHours > 0 && shelfHours <= 12;
                    const emoji = cropName === 'Tomato' ? '🍅' : cropName === 'Banana' ? '🍌' : cropName === 'Brinjal' ? '🍆' : cropName === 'Green Chilli' ? '🌶️' : '🧅';
                    const listedAt = new Date(l.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' });

                    return (
                      <tr key={l.id}>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--slate-900)' }}>{farmerName}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--slate-500)' }}>
                            {l.self_delivery ? '🚗 Self-delivery' : '📦 Hub pickup'}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                            <span style={{ fontSize: '1.1rem' }}>{emoji}</span>
                            <div>
                              <strong>{cropName}</strong>
                              <span className="badge badge-neutral" style={{ marginLeft: '6px' }}>Grade {l.grade}</span>
                            </div>
                          </div>
                        </td>
                        <td className="tabular">
                          <strong>{l.available_kg} kg</strong>
                          <div style={{ fontSize: '0.72rem', color: 'var(--slate-500)' }}>of {l.quantity_kg} kg</div>
                        </td>
                        <td>
                          <div>{l.village}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--slate-500)' }}>{l.district}</div>
                        </td>
                        <td>
                          {shelfHours > 0 ? (
                            <span style={{ fontWeight: 700, color: isExpiring ? 'var(--amber-700)' : 'var(--primary-700)' }}>
                              ⏱ {shelfHours.toFixed(1)}h
                            </span>
                          ) : (
                            <span style={{ color: 'var(--slate-400)' }}>—</span>
                          )}
                          {isExpiring && (
                            <div style={{ fontSize: '0.68rem', color: 'var(--amber-600)', fontWeight: 600 }}>Urgent!</div>
                          )}
                        </td>
                        <td className="tabular">
                          {(l as any).price_recommendation?.floor_price ? (
                            <span style={{ fontWeight: 700, color: 'var(--primary-700)' }}>
                              ₹{(l as any).price_recommendation.floor_price}/kg
                            </span>
                          ) : (
                            <span style={{ color: 'var(--slate-400)' }}>—</span>
                          )}
                        </td>
                        <td>
                          <span className={`badge ${
                            l.status === 'ACTIVE' ? 'badge-success' :
                            l.status === 'RESERVED' ? 'badge-warning' :
                            l.status === 'IN_LOT' ? 'badge-info' :
                            l.status === 'EXPIRED' ? 'badge-danger' : 'badge-neutral'
                          }`}>{l.status}</span>
                        </td>
                        <td style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>{listedAt}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Active Lots Pipeline ─────────────────────────────────────────── */}
      {currentTab === 'admin_dashboard' && (
        <div className="card" style={{ padding: '24px', marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', color: 'var(--slate-900)' }}>Active Lots Pipeline</h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
                Full transaction lifecycle: Matching → Escrow → In Transit → Quality Gate → Settlement
              </p>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={loadData}>
              Refresh Pipeline
            </button>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lot Code</th>
                  <th>Crop & Grade</th>
                  <th>Total Qty</th>
                  <th>Floor (F)</th>
                  <th>MVP</th>
                  <th>Agreed Price</th>
                  <th>Status</th>
                  <th>Ops Actions</th>
                </tr>
              </thead>
              <tbody>
                {lots.map((l) => {
                  const cropName = typeof l.crop === 'object' ? l.crop.name : l.crop;

                  return (
                    <tr key={l.id}>
                      <td style={{ fontWeight: 700 }} className="tabular">{l.lot_code}</td>
                      <td>
                        <strong>{cropName}</strong>
                        <span className="badge badge-neutral" style={{ marginLeft: '6px' }}>Grade {l.grade}</span>
                      </td>
                      <td className="tabular"><strong>{l.total_quantity_kg} kg</strong></td>
                      <td className="tabular">₹{l.floor_price_per_kg}/kg</td>
                      <td className="tabular" style={{ color: 'var(--primary-700)', fontWeight: 700 }}>₹{l.minimum_viable_price_per_kg}/kg</td>
                      <td className="tabular">₹{l.agreed_price_per_kg || '35.00'}/kg</td>
                      <td>
                        <span className={`badge ${
                          l.status === 'SETTLED' ? 'badge-success' :
                          l.status === 'ESCROW_FUNDED' ? 'badge-info' :
                          l.status === 'PROPOSED' ? 'badge-warning' : 'badge-neutral'
                        }`}>
                          {l.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => {
                              setSelectedLot(l);
                              onTabChange('logistics_planner');
                              handlePlanRoute(l.id);
                            }}
                          >
                            <Truck size={13} /> Route Plan
                          </button>
                          
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => {
                              setSelectedLot(l);
                              setShowQualityModal(true);
                            }}
                          >
                            <Scale size={13} /> Quality
                          </button>

                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handleExecuteSettlement(l.id)}
                            disabled={settling}
                          >
                            <DollarSign size={13} /> Settle
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Logistics Planner Tab (Leaflet Interactive Map & CVRP Solution) */}
      {currentTab === 'logistics_planner' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Consolidation Decision Card */}
          <div className="card" style={{ padding: '24px', background: 'linear-gradient(135deg, #ffffff 0%, var(--primary-50) 100%)', border: '1px solid var(--primary-300)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <span className="badge badge-success" style={{ marginBottom: '6px' }}>Consolidation Decision (§16.1 & D1 §5)</span>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--primary-900)' }}>
                  Aggregated Hub Routing is Cheaper by ₹1,420.00
                </h3>
              </div>
              <span className="badge badge-info">Applied Trunk Tier 2: ₹0.45/kg/km (500 kg)</span>
            </div>

            <div className="grid-3">
              <div style={{ background: '#ffffff', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)', textTransform: 'uppercase', fontWeight: 600 }}>Direct Point-to-Point Cost</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--danger-600)' }} className="tabular">₹8,514.00</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>4 separate farmer-to-buyer trips</div>
              </div>

              <div style={{ background: '#ffffff', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)', textTransform: 'uppercase', fontWeight: 600 }}>Consolidated Hub Cost (L_lot)</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--primary-700)' }} className="tabular">₹7,094.00</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>Collection + Handling + Bulk Trunk</div>
              </div>

              <div style={{ background: '#ffffff', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)', textTransform: 'uppercase', fontWeight: 600 }}>Vehicle Capacity Utilization</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--slate-900)' }} className="tabular">50.0% (500/1,000kg)</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>Vehicle TN59AB1234 (Mini Truck)</div>
              </div>
            </div>
          </div>

          {/* Interactive Route Map & Stops */}
          <div className="grid-2" style={{ gridTemplateColumns: '1.2fr 0.8fr' }}>
            <div className="card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Truck size={18} color="var(--primary-700)" />
                  <h3 style={{ fontSize: '1rem', color: 'var(--slate-900)' }}>
                    OR-Tools CVRP Solved Route Polyline
                  </h3>
                </div>
                <span className="badge badge-success">Feasible (Deadline: Met)</span>
              </div>
              
              <LeafletRouteMap stops={demoStops} height="440px" />
            </div>

            {/* Route Stops Table */}
            <div className="card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', marginBottom: '12px', color: 'var(--slate-900)' }}>
                Scheduled Waypoints ({demoStops.length} Stops)
              </h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {demoStops.map((s) => (
                  <div
                    key={s.sequence}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 12px',
                      background: 'var(--slate-50)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--slate-200)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{
                        width: '24px', height: '24px', borderRadius: '50%',
                        background: s.stop_type === 'PICKUP' ? 'var(--primary-600)' : s.stop_type === 'AGGREGATION' ? '#2563eb' : 'var(--amber-600)',
                        color: '#fff', fontSize: '11px', fontWeight: 800,
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                      }}>
                        {s.sequence}
                      </div>
                      <div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--slate-900)' }}>{s.location_name}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>
                          {s.stop_type === 'PICKUP' ? `Pickup: ${s.quantity_kg} kg` : s.stop_type === 'AGGREGATION' ? 'Depot Intake & Weigh' : 'Final Delivery'}
                        </div>
                      </div>
                    </div>
                    <span className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>Verified ✓</span>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--slate-200)' }}>
                <button
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '12px' }}
                  onClick={() => alert("Route dispatched to driver TN59AB1234. GPS tracking active.")}
                >
                  <Play size={15} /> Dispatch Vehicle & Start Route
                </button>
              </div>
            </div>
          </div>

        </div>
      )}

      {/* Anti-Waste Rejection Recovery Tab (D3 Headline Demo) */}
      {currentTab === 'rejection_recovery' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <div className="card" style={{ padding: '24px', background: 'linear-gradient(135deg, #fffbeb 0%, #ffffff 100%)', border: '1px solid var(--amber-300)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <span className="badge badge-warning" style={{ marginBottom: '6px' }}>Anti-Waste Rejection Recovery Engine (§16.4 & D3)</span>
                <h2 style={{ fontSize: '1.4rem', color: 'var(--amber-900)' }}>
                  150 kg Tomato Rejected at Handover — Finding Second Sale
                </h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--amber-800)', maxWidth: '700px', marginTop: '4px' }}>
                  Instead of writing off rejected produce as landfill waste, the engine immediately evaluates destination feasibility & economics on the remaining shelf-life.
                </p>
              </div>

              <div style={{ background: '#ffffff', padding: '12px 20px', borderRadius: 'var(--radius-md)', border: '1px solid var(--amber-300)', textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)', textTransform: 'uppercase', fontWeight: 600 }}>Potential Recovered Value</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary-700)' }} className="tabular">₹3,300.00</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>150 kg @ ₹22.00/kg</div>
              </div>
            </div>
          </div>

          {/* Destination Candidates Ranking Table */}
          <div className="card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', color: 'var(--slate-900)' }}>Ranked Alternative Destinations</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
                  Judicial table showing both feasible destinations and excluded candidates with their exact rejection reason.
                </p>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => handleEvaluateDestinations(selectedLot?.id || '')}>
                Re-evaluate
              </button>
            </div>

            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Buyer / Destination</th>
                    <th>Type</th>
                    <th>Distance & Time</th>
                    <th>Gross Price</th>
                    <th>Net Return / kg</th>
                    <th>Feasibility</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Destination 1: Sri Anandha Hotels (Feasible) */}
                  <tr style={{ background: 'var(--primary-50)' }}>
                    <td>
                      <strong>Sri Anandha Hotels</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>Theni • Accepted Grades: A, B</div>
                    </td>
                    <td><span className="badge badge-info">SECONDARY</span></td>
                    <td>
                      <div>12.0 km (0.3h transit)</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--primary-700)', fontWeight: 600 }}>Shelf-life margin: +9.7h</div>
                    </td>
                    <td className="tabular">₹22.00/kg</td>
                    <td className="tabular" style={{ color: 'var(--primary-800)', fontWeight: 800 }}>
                      ₹19.80/kg
                    </td>
                    <td>
                      <span className="badge badge-success">✓ FEASIBLE</span>
                    </td>
                    <td>
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={handleExecuteRecovery}
                        disabled={recovering}
                      >
                        {recovering ? 'Routing...' : 'Sell to Anandha'}
                      </button>
                    </td>
                  </tr>

                  {/* Destination 2: Kodai Foods Processing (Feasible) */}
                  <tr>
                    <td>
                      <strong>Kodai Foods Processing</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>Theni • Accepted Grades: B, C</div>
                    </td>
                    <td><span className="badge badge-neutral">PROCESSOR</span></td>
                    <td>
                      <div>18.0 km (0.5h transit)</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--primary-700)' }}>Shelf-life margin: +9.5h</div>
                    </td>
                    <td className="tabular">₹14.00/kg</td>
                    <td className="tabular" style={{ fontWeight: 700 }}>₹11.90/kg</td>
                    <td><span className="badge badge-success">✓ FEASIBLE</span></td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={handleExecuteRecovery}>
                        Sell to Kodai
                      </button>
                    </td>
                  </tr>

                  {/* Destination 3: Chennai Metro Grocers (Infeasible - Shelf Life) */}
                  <tr style={{ opacity: 0.7 }}>
                    <td>
                      <strong>Chennai Metro Grocers</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>Chennai • Accepted Grades: A</div>
                    </td>
                    <td><span className="badge badge-neutral">PREMIUM</span></td>
                    <td>470.0 km (13.4h transit)</td>
                    <td className="tabular">₹38.00/kg</td>
                    <td className="tabular">₹18.40/kg</td>
                    <td>
                      <span className="badge badge-danger">REJECTED: SHELF_LIFE</span>
                      <div style={{ fontSize: '0.7rem', color: 'var(--danger-600)' }}>Transit (13.4h) &gt; Shelf Life (10h)</div>
                    </td>
                    <td>
                      <button className="btn btn-secondary btn-sm" disabled>Infeasible</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {recoverySuccess && (
              <div style={{ marginTop: '20px', padding: '14px', background: 'var(--primary-100)', color: 'var(--primary-900)', borderRadius: 'var(--radius-md)', fontWeight: 600 }}>
                ✓ {recoverySuccess}
              </div>
            )}
          </div>

        </div>
      )}

      {/* Quality Check Modal */}
      {showQualityModal && (
        <div className="modal-overlay" onClick={() => setShowQualityModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
              <h3 style={{ fontSize: '1.25rem', color: 'var(--slate-900)' }}>Handover Quality Verification</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowQualityModal(false)}>✕</button>
            </div>

            <div style={{ marginBottom: '14px', padding: '12px', background: 'var(--slate-50)', borderRadius: 'var(--radius-md)', fontSize: '0.85rem' }}>
              Lot: <strong>{selectedLot?.lot_code}</strong> • Total Quantity: <strong>{selectedLot?.total_quantity_kg} kg</strong>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Accepted Quantity (kg)</label>
                <input
                  type="number"
                  className="input tabular"
                  value={acceptedQty}
                  onChange={(e) => setAcceptedQty(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Rejected Quantity (kg)</label>
                <input
                  type="number"
                  className="input tabular"
                  value={rejectedQty}
                  onChange={(e) => setRejectedQty(e.target.value)}
                />
              </div>
            </div>

            {parseFloat(rejectedQty) > 0 && (
              <div className="form-group">
                <label className="form-label">Rejection Reason</label>
                <select className="select" value={rejectionReason} onChange={(e) => setRejectionReason(e.target.value)}>
                  <option value="GRADE_MISMATCH">Grade Mismatch (Sub-Grade B)</option>
                  <option value="MINOR_DEFECTS">Minor Surface Defects</option>
                  <option value="OVERRIPE">Overripe / Soft Texture</option>
                </select>
                <span className="form-hint">On submit, the anti-waste recovery engine will find secondary buyer options.</span>
              </div>
            )}

            <button
              className="btn btn-primary"
              style={{ width: '100%', padding: '12px', marginTop: '16px' }}
              onClick={handleSubmitQualityCheck}
              disabled={submittingCheck}
            >
              {submittingCheck ? 'Submitting...' : 'Record Handover Inspection'}
            </button>
          </div>
        </div>
      )}

    </div>
  );
};
