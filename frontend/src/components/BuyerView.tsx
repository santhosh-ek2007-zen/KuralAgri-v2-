import React, { useState, useEffect } from 'react';
import { api, BuyerOrder, Lot, PriceBreakdown, Crop, Region } from '../api';
import { ShoppingBag, Search, CheckCircle, ArrowRight, ShieldCheck, DollarSign, Users, Truck, AlertCircle } from 'lucide-react';

export const BuyerView: React.FC = () => {
  const [orders, setOrders] = useState<BuyerOrder[]>([]);
  const [crops, setCrops] = useState<Crop[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);

  // Post Requirement Modal
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [selectedCrop, setSelectedCrop] = useState('');
  const [selectedGrade, setSelectedGrade] = useState<'A' | 'B' | 'C'>('A');
  const [quantityKg, setQuantityKg] = useState('500');
  const [maxPrice, setMaxPrice] = useState('35.00');
  const [sourcingPref, setSourcingPref] = useState<'AGGREGATED' | 'SINGLE_SOURCE'>('AGGREGATED');
  const [allowPartial, setAllowPartial] = useState(true);
  const [minQty, setMinQty] = useState('400');
  const [posting, setPosting] = useState(false);

  // Matching & Proposal
  const [matchingOrderId, setMatchingOrderId] = useState<string | null>(null);
  const [matchedLot, setMatchedLot] = useState<Lot | null>(null);
  const [matchedBreakdown, setMatchedBreakdown] = useState<PriceBreakdown | null>(null);
  const [agreedPrice, setAgreedPrice] = useState('35.00');
  const [accepting, setAccepting] = useState(false);

  // Escrow funding
  const [fundingLot, setFundingLot] = useState<Lot | null>(null);
  const [isFunding, setIsFunding] = useState(false);
  const [fundingSuccess, setFundingSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [orderRes, cropRes, regRes] = await Promise.all([
        api.getBuyerOrders(),
        api.getCrops(),
        api.getRegions(),
      ]);
      setOrders(orderRes);
      setCrops(cropRes);
      setRegions(regRes);
      if (cropRes.length > 0) setSelectedCrop(cropRes[0].id);
    } catch (err) {
      console.error('Failed to load buyer data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePostOrder = async () => {
    try {
      setPosting(true);
      const deadline = new Date();
      deadline.setDate(deadline.getDate() + 2);

      await api.createBuyerOrder({
        crop: selectedCrop,
        grade: selectedGrade,
        quantity_kg: parseFloat(quantityKg),
        delivery_deadline: deadline.toISOString(),
        max_price_per_kg: parseFloat(maxPrice),
        sourcing_preference: sourcingPref,
        allow_partial: allowPartial,
        min_acceptable_quantity_kg: allowPartial ? parseFloat(minQty) : undefined,
        delivery_district: 'Theni',
        delivery_latitude: '9.9457',
        delivery_longitude: '77.4779',
      });

      setShowOrderModal(false);
      loadData();
    } catch (err: any) {
      alert(`Error creating buyer requirement: ${err.message}`);
    } finally {
      setPosting(false);
    }
  };

  const handleRunMatching = async (orderId: string) => {
    try {
      setMatchingOrderId(orderId);
      const res = await api.matchBuyerOrder(orderId);
      setMatchedLot(res.lot);
      setMatchedBreakdown(res.breakdown);
      setAgreedPrice(res.lot.agreed_price_per_kg || '35.00');
    } catch (err: any) {
      alert(`Matching result: ${err.message}`);
    } finally {
      setMatchingOrderId(null);
    }
  };

  const handleAcceptLot = async () => {
    if (!matchedLot) return;
    try {
      setAccepting(true);
      const res = await api.acceptLot(matchedLot.id, agreedPrice);
      setMatchedLot(res.lot);
      setFundingLot(res.lot);
      loadData();
    } catch (err: any) {
      alert(`Error accepting lot: ${err.message}`);
    } finally {
      setAccepting(false);
    }
  };

  const handleConfirmEscrow = async () => {
    if (!fundingLot) return;
    try {
      setIsFunding(true);
      const fundRes = await api.fundEscrow(fundingLot.id);
      const advRes = await api.releaseAdvances(fundingLot.id);
      setFundingSuccess(`Escrow ₹${fundRes.total_received} funded. Advances released to ${advRes.advances_count} farmers.`);
      loadData();
    } catch (err: any) {
      alert(`Escrow funding error: ${err.message}`);
    } finally {
      setIsFunding(false);
    }
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
      
      {/* Buyer Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
        borderRadius: 'var(--radius-xl)',
        padding: '28px 32px',
        color: '#ffffff',
        marginBottom: '28px',
        boxShadow: 'var(--shadow-lg)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span className="badge badge-info">Bulk Procurement • Theni Fresh Mart</span>
              <span className="badge badge-success">Single-Grade Guarantee</span>
            </div>
            <h1 style={{ color: '#fff', fontSize: '1.85rem', marginBottom: '6px' }}>
              Procurement & Lot Matching Console
            </h1>
            <p style={{ color: 'var(--slate-400)', fontSize: '0.95rem', maxWidth: '650px' }}>
              Sourcing graded lots aggregated from certified smallholders. All lots include logistics cost, protected farmer floor, and transparent escrow waterfall.
            </p>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => setShowOrderModal(true)}
            style={{ padding: '12px 24px', fontSize: '1rem' }}
          >
            <ShoppingBag size={18} />
            Post Sourcing Requirement
          </button>
        </div>
      </div>

      {/* Sourcing Requirements Table */}
      <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', color: 'var(--slate-900)' }}>Your Sourcing Requirements</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
              Click "Find Supply / Match Lot" to greedily assemble a single-crop, single-grade Lot from active farmer listings.
            </p>
          </div>
          <span className="badge badge-neutral">{orders.length} Requirements</span>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--slate-500)' }}>Loading requirements...</div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order Code</th>
                  <th>Crop & Grade</th>
                  <th>Quantity Needed</th>
                  <th>Delivery Location</th>
                  <th>Max Price Ceiling</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => {
                  const cropName = typeof o.crop === 'object' ? o.crop.name : o.crop;
                  const isMatching = matchingOrderId === o.id;

                  return (
                    <tr key={o.id}>
                      <td style={{ fontWeight: 700, color: 'var(--slate-900)' }} className="tabular">
                        {o.order_code}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '1.1rem' }}>🍅</span>
                          <div>
                            <strong>{cropName}</strong>
                            <span className="badge badge-neutral" style={{ marginLeft: '6px' }}>Grade {o.grade}</span>
                          </div>
                        </div>
                      </td>
                      <td className="tabular">
                        <strong>{o.quantity_kg} kg</strong>
                        {o.allow_partial && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>min {o.min_acceptable_quantity_kg} kg</div>
                        )}
                      </td>
                      <td>
                        <div>{o.delivery_district}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>Deadline: 2 days</div>
                      </td>
                      <td className="tabular">
                        <strong style={{ color: 'var(--slate-900)' }}>₹{o.max_price_per_kg || '35.00'}/kg</strong>
                      </td>
                      <td>
                        <span className={`badge ${o.status === 'OPEN' ? 'badge-info' : o.status === 'MATCHED' ? 'badge-success' : 'badge-neutral'}`}>
                          {o.status}
                        </span>
                      </td>
                      <td>
                        {o.status === 'OPEN' && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handleRunMatching(o.id)}
                            disabled={isMatching}
                          >
                            <Search size={14} />
                            {isMatching ? 'Matching...' : 'Find Supply (Match)'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Matched Lot Proposal Card (D1 §10 Worked Example Display) */}
      {matchedLot && matchedBreakdown && (
        <div className="card" style={{ padding: '28px', marginBottom: '32px', border: '2px solid var(--primary-500)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span className="badge badge-success" style={{ fontSize: '0.8rem' }}>Matched Lot Proposal</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.9rem', color: 'var(--slate-700)' }}>
                  {matchedLot.lot_code}
                </span>
              </div>
              <h2 style={{ fontSize: '1.4rem', color: 'var(--slate-900)' }}>
                {matchedLot.total_quantity_kg} kg Tomato [Grade {matchedLot.grade}] Consolidation
              </h2>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)', textTransform: 'uppercase', fontWeight: 600 }}>Minimum Viable Price (MVP)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary-700)' }} className="tabular">
                  ₹{matchedBreakdown.minimum_viable_lot_price}/kg
                </div>
              </div>
            </div>
          </div>

          {/* Viability Banner */}
          <div style={{
            background: matchedBreakdown.is_viable ? 'var(--primary-50)' : 'var(--danger-50)',
            border: `1px solid ${matchedBreakdown.is_viable ? 'var(--primary-200)' : 'var(--danger-200)'}`,
            borderRadius: 'var(--radius-md)',
            padding: '12px 16px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}>
            {matchedBreakdown.is_viable ? (
              <CheckCircle size={18} color="var(--primary-700)" />
            ) : (
              <AlertCircle size={18} color="var(--danger-600)" />
            )}
            <div style={{ fontSize: '0.85rem', color: matchedBreakdown.is_viable ? 'var(--primary-900)' : 'var(--danger-800)', fontWeight: 600 }}>
              {matchedBreakdown.is_viable
                ? `VIABLE TRANSACTION: Minimum Viable Price ₹${matchedBreakdown.minimum_viable_lot_price}/kg is within your ceiling of ₹${matchedBreakdown.buyer_ceiling_per_kg}/kg.`
                : `NOT VIABLE: Minimum Viable Price ₹${matchedBreakdown.minimum_viable_lot_price}/kg exceeds ceiling.`}
            </div>
          </div>

          {/* Contributor Farmers Grid */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Users size={16} color="var(--slate-700)" />
              <h3 style={{ fontSize: '1rem', color: 'var(--slate-800)' }}>
                Contributing Smallholders ({matchedBreakdown.contributors.length} Farmers)
              </h3>
            </div>
            
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Farmer</th>
                    <th>Village</th>
                    <th>Quantity</th>
                    <th>Advance Rate (Tier)</th>
                    <th>Advance Paid (Pos)</th>
                    <th>Estimated Settlement</th>
                    <th>Mandi Channel Uplift</th>
                  </tr>
                </thead>
                <tbody>
                  {matchedBreakdown.contributors.map((c, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{c.farmer_name}</td>
                      <td>{c.village}</td>
                      <td className="tabular"><strong>{c.quantity_kg} kg</strong></td>
                      <td>
                        <span className="badge badge-neutral">
                          {i === 0 || i === 2 ? 'Tier NEW (50%)' : i === 1 ? 'Tier T1_3 (60%)' : 'Tier T10+ (70%)'}
                        </span>
                      </td>
                      <td className="tabular" style={{ color: 'var(--primary-700)', fontWeight: 700 }}>₹{c.advance_amount}</td>
                      <td className="tabular">₹{c.estimated_settlement}</td>
                      <td className="tabular">
                        <span className="badge badge-success">+{c.estimated_uplift_pct}%</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* D1 §10 Cost Breakdown Panel */}
          <div className="grid-2" style={{ marginBottom: '24px' }}>
            <div style={{ background: 'var(--slate-50)', padding: '18px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--slate-200)' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '12px', color: 'var(--slate-800)' }}>
                Itemised Financial Math (D1 §10 Worked Example)
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--slate-600)' }}>Protected Farmer Floor (F):</span>
                  <strong className="tabular">₹{matchedBreakdown.floor_price_per_kg}/kg</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--slate-600)' }}>Logistics Cost (L_lot):</span>
                  <strong className="tabular">₹{matchedBreakdown.logistics_total} (₹{matchedBreakdown.logistics_per_kg}/kg)</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--slate-600)' }}>Lender Claim (Advances + Interest):</span>
                  <strong className="tabular">₹{matchedBreakdown.lender_claim_total}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--slate-600)' }}>Platform Fee (4%):</span>
                  <strong className="tabular">₹{matchedBreakdown.platform_fee_total}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--slate-600)' }}>Risk Reserve (1%):</span>
                  <strong className="tabular">₹{matchedBreakdown.risk_reserve_total}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--slate-300)', paddingTop: '8px' }}>
                  <span style={{ fontWeight: 700 }}>Farmer Residual Pool:</span>
                  <strong className="tabular" style={{ color: 'var(--primary-700)' }}>₹{matchedBreakdown.farmer_residual_pool}</strong>
                </div>
              </div>
            </div>

            {/* Price Acceptance & Action */}
            <div style={{ background: '#ffffff', padding: '18px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--slate-200)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <h4 style={{ fontSize: '0.9rem', marginBottom: '10px', color: 'var(--slate-800)' }}>
                  Accept & Contract Price
                </h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--slate-500)', marginBottom: '14px' }}>
                  Contract must satisfy: <strong>MVP ₹{matchedBreakdown.minimum_viable_lot_price} ≤ Price ≤ Ceiling ₹{matchedBreakdown.buyer_ceiling_per_kg}</strong>.
                </p>

                <div className="form-group">
                  <label className="form-label">Agreed Price per kg (₹)</label>
                  <input
                    type="number"
                    step="0.50"
                    className="input tabular"
                    value={agreedPrice}
                    onChange={(e) => setAgreedPrice(e.target.value)}
                    style={{ fontSize: '1.2rem', fontWeight: 800 }}
                  />
                  <span className="form-hint">
                    Total Contract Value: <strong className="tabular">₹{(parseFloat(agreedPrice || '0') * parseFloat(matchedLot.total_quantity_kg)).toFixed(2)}</strong>
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
                <button
                  className="btn btn-primary"
                  style={{ flex: 1, padding: '12px' }}
                  onClick={handleAcceptLot}
                  disabled={accepting || matchedLot.status !== 'PROPOSED'}
                >
                  <CheckCircle size={16} />
                  {matchedLot.status === 'ACCEPTED' ? 'Lot Accepted' : accepting ? 'Accepting...' : 'Accept Lot & Proceed to Escrow'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Escrow Funding Modal / Dialog */}
      {fundingLot && (
        <div className="modal-overlay" onClick={() => setFundingLot(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '680px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={22} color="var(--primary-700)" />
                <h3 style={{ fontSize: '1.25rem', color: 'var(--slate-900)' }}>Fund Simulated Escrow Account</h3>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setFundingLot(null)}>✕</button>
            </div>

            <div style={{ marginBottom: '16px', background: 'var(--amber-50)', border: '1px solid var(--amber-200)', padding: '12px 16px', borderRadius: 'var(--radius-md)' }}>
              <span className="badge badge-warning" style={{ marginBottom: '4px' }}>Simulated Escrow Rails</span>
              <p style={{ fontSize: '0.8rem', color: 'var(--amber-800)' }}>
                Funds are held in platform trust before pickup (D1 §13). Upon confirmation, point-of-sale advances are immediately credited to all 4 contributing farmers.
              </p>
            </div>

            {/* Waterfall Breakdown Preview */}
            <div style={{ background: 'var(--slate-50)', padding: '18px', borderRadius: 'var(--radius-lg)', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 600 }}>Total Deposit Required:</span>
                <span style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--slate-900)' }} className="tabular">
                  ₹{(parseFloat(fundingLot.agreed_price_per_kg || agreedPrice) * parseFloat(fundingLot.total_quantity_kg)).toFixed(2)}
                </span>
              </div>

              {/* Stacked Waterfall visualizer */}
              <div style={{ display: 'flex', height: '24px', borderRadius: '6px', overflow: 'hidden', margin: '14px 0 8px 0' }}>
                <div style={{ width: '28%', background: '#3b82f6' }} title="Lender Advance & Interest" />
                <div style={{ width: '40%', background: '#f59e0b' }} title="Logistics Cost" />
                <div style={{ width: '4%', background: '#8b5cf6' }} title="Platform Fee" />
                <div style={{ width: '1%', background: '#ec4899' }} title="Risk Reserve" />
                <div style={{ width: '27%', background: '#10b981' }} title="Farmer Settlement Pool" />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--slate-500)' }}>
                <span>🔵 Advances (₹4,873)</span>
                <span>🟡 Logistics (₹7,094)</span>
                <span>🟣 Platform (₹700)</span>
                <span>🟢 Farmer Pool (₹4,657)</span>
              </div>
            </div>

            {fundingSuccess ? (
              <div style={{ padding: '16px', background: 'var(--primary-50)', borderRadius: 'var(--radius-md)', color: 'var(--primary-800)', fontWeight: 600, textAlign: 'center', marginBottom: '16px' }}>
                ✓ {fundingSuccess}
              </div>
            ) : (
              <button
                className="btn btn-primary"
                style={{ width: '100%', padding: '14px', fontSize: '1rem', fontWeight: 700 }}
                onClick={handleConfirmEscrow}
                disabled={isFunding}
              >
                {isFunding ? 'Executing Escrow Deposit...' : 'Confirm Escrow Deposit (₹17,500.00)'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Post Requirement Modal */}
      {showOrderModal && (
        <div className="modal-overlay" onClick={() => setShowOrderModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.25rem', color: 'var(--slate-900)' }}>Post Sourcing Requirement</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowOrderModal(false)}>✕</button>
            </div>

            <div className="form-group">
              <label className="form-label">Crop & Commodity</label>
              <select className="select" value={selectedCrop} onChange={(e) => setSelectedCrop(e.target.value)}>
                {crops.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} ({c.category})</option>
                ))}
              </select>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Grade</label>
                <select className="select" value={selectedGrade} onChange={(e) => setSelectedGrade(e.target.value as any)}>
                  <option value="A">Grade A (Premium Retail)</option>
                  <option value="B">Grade B (Secondary / Hotels)</option>
                  <option value="C">Grade C (Processing)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Quantity Needed (kg)</label>
                <input
                  type="number"
                  className="input tabular"
                  value={quantityKg}
                  onChange={(e) => setQuantityKg(e.target.value)}
                />
              </div>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Max Price Ceiling (₹/kg)</label>
                <input
                  type="number"
                  step="0.50"
                  className="input tabular"
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(e.target.value)}
                />
                <span className="form-hint">Retail-linked ceiling: ₹35.00/kg</span>
              </div>
              <div className="form-group">
                <label className="form-label">Sourcing Preference</label>
                <select className="select" value={sourcingPref} onChange={(e) => setSourcingPref(e.target.value as any)}>
                  <option value="AGGREGATED">Aggregated Multi-Farmer Lot</option>
                  <option value="SINGLE_SOURCE">Single Farm Direct</option>
                </select>
              </div>
            </div>

            <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '10px' }}>
              <input
                type="checkbox"
                id="partial_allow"
                checked={allowPartial}
                onChange={(e) => setAllowPartial(e.target.checked)}
                style={{ width: '16px', height: '16px' }}
              />
              <label htmlFor="partial_allow" style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                Allow Partial Fulfilment (Min: {minQty} kg)
              </label>
            </div>

            <button
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '16px', padding: '12px' }}
              onClick={handlePostOrder}
              disabled={posting}
            >
              {posting ? 'Posting...' : 'Post Requirement'}
            </button>
          </div>
        </div>
      )}

    </div>
  );
};
