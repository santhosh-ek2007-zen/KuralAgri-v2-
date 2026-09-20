import React, { useState, useEffect } from 'react';
import { api, Listing, Crop, Region, PriceRecommendation } from '../api';
import { PlusCircle, Clock, ShieldCheck, TrendingUp, AlertTriangle, ArrowRight, CheckCircle2, ChevronRight, Info } from 'lucide-react';

export const FarmerView: React.FC = () => {
  const [listings, setListings] = useState<Listing[]>([]);
  const [crops, setCrops] = useState<Crop[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [step, setStep] = useState(1);
  const [selectedCrop, setSelectedCrop] = useState<string>('');
  const [selectedGrade, setSelectedGrade] = useState<'A' | 'B' | 'C'>('A');
  const [quantityKg, setQuantityKg] = useState<string>('150');
  const [village, setVillage] = useState<string>('Cumbum');
  const [district, setDistrict] = useState<string>('Theni');
  const [selfDelivery, setSelfDelivery] = useState<boolean>(false);
  const [harvestHoursAgo, setHarvestHoursAgo] = useState<number>(26);

  // Price Intelligence recommendation state
  const [recommendation, setRecommendation] = useState<PriceRecommendation | null>(null);
  const [loadingRec, setLoadingRec] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [listRes, cropRes, regRes] = await Promise.all([
        api.getListings(),
        api.getCrops(),
        api.getRegions(),
      ]);
      setListings(listRes);
      setCrops(cropRes);
      setRegions(regRes);
      if (cropRes.length > 0) setSelectedCrop(cropRes[0].id);
    } catch (err) {
      console.error('Failed to load farmer data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchRecommendation = async () => {
    try {
      setLoadingRec(true);
      const now = new Date();
      now.setHours(now.getHours() - harvestHoursAgo);
      const harvestDt = now.toISOString();

      const theniRegion = regions.find(r => r.name.toLowerCase() === district.toLowerCase()) || regions[0];

      const rec = await api.getPriceRecommendation({
        crop: selectedCrop,
        region: theniRegion?.id || '',
        grade: selectedGrade,
        harvest_datetime: harvestDt,
        quantity_kg: quantityKg,
      });
      setRecommendation(rec);
      setStep(3);
    } catch (err: any) {
      alert(`Error computing price recommendation: ${err.message}`);
    } finally {
      setLoadingRec(false);
    }
  };

  const handlePublishListing = async () => {
    try {
      setPublishing(true);
      const now = new Date();
      now.setHours(now.getHours() - harvestHoursAgo);

      await api.createListing({
        crop: selectedCrop,
        grade: selectedGrade,
        quantity_kg: parseFloat(quantityKg),
        harvest_datetime: now.toISOString(),
        village,
        district,
        latitude: '9.7200',
        longitude: '77.2800',
        self_delivery: selfDelivery,
      });

      setShowCreateModal(false);
      setStep(1);
      loadData();
    } catch (err: any) {
      alert(`Error publishing listing: ${err.message}`);
    } finally {
      setPublishing(false);
    }
  };

  const currentCropObj = crops.find(c => c.id === selectedCrop);

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
      
      {/* Top Banner: Earnings & Channel Uplift Guarantee */}
      <div style={{
        background: 'linear-gradient(135deg, #166534 0%, #15803d 50%, #14532d 100%)',
        borderRadius: 'var(--radius-xl)',
        padding: '28px 32px',
        color: '#ffffff',
        marginBottom: '28px',
        boxShadow: 'var(--shadow-lg)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '20px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span className="badge" style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)' }}>
                  Farmer Hub • Theni Region
                </span>
                <span className="badge" style={{ background: 'var(--amber-500)', color: '#000', fontWeight: 700 }}>
                  Tier NEW (50% Advance Guaranteed)
                </span>
              </div>
              <h1 style={{ color: '#fff', fontSize: '1.85rem', marginBottom: '6px' }}>
                Vanakkam, Ravi Kumar
              </h1>
              <p style={{ color: 'rgba(255, 255, 255, 0.85)', fontSize: '0.95rem', maxWidth: '600px' }}>
                Your produce is protected by guaranteed floor pricing, immediate point-of-sale advances, and zero debt liability on crop failure.
              </p>
            </div>

            <button
              className="btn"
              onClick={() => setShowCreateModal(true)}
              style={{
                background: '#ffffff',
                color: 'var(--primary-800)',
                fontSize: '1rem',
                fontWeight: 700,
                padding: '12px 24px',
                boxShadow: 'var(--shadow-md)',
              }}
            >
              <PlusCircle size={18} />
              List Harvested Produce
            </button>
          </div>

          {/* KPI Metrics */}
          <div className="grid-4" style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.15)' }}>
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>Total Realisation</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, marginTop: '2px' }} className="tabular">₹1,264.80</div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>Across settled demo lots</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>Advance Received</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, marginTop: '2px' }} className="tabular">₹660.00</div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>Disbursed before collection</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>Settlement Received</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, marginTop: '2px' }} className="tabular">₹604.80</div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>Post-handover waterfall</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>Income Uplift vs Mandi</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fef08a', marginTop: '2px' }} className="tabular">+27.0%</div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>vs ₹25.00 traditional 60% net</div>
            </div>
          </div>
        </div>
      </div>

      {/* Market Pulse Ribbon */}
      <div className="card" style={{ padding: '14px 20px', marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px', background: '#ffffff' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.25rem' }}>🍅</span>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--slate-900)' }}>Theni Tomato Market Pulse (§16.2)</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>Updated modal price & supply trends</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--slate-500)', display: 'block' }}>Mandi Benchmark</span>
            <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--slate-900)' }} className="tabular">₹25.00/kg</span>
          </div>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--slate-500)', display: 'block' }}>Arrivals Trend</span>
            <span className="badge badge-danger">Declining -18% (Low Supply)</span>
          </div>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--slate-500)', display: 'block' }}>Weather Risk</span>
            <span className="badge badge-warning">Heavy Rain (High Risk)</span>
          </div>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--slate-500)', display: 'block' }}>Protected Floor (F)</span>
            <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--primary-700)' }} className="tabular">₹16.50/kg</span>
          </div>
        </div>
      </div>

      {/* Active Listings Section */}
      <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', color: 'var(--slate-900)' }}>Your Produce Listings</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
              Active produce available for buyer matching. Remaining shelf-life dynamically gates destination feasibility.
            </p>
          </div>
          <span className="badge badge-neutral">{listings.length} Listings</span>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--slate-500)' }}>Loading listings...</div>
        ) : listings.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', border: '1px dashed var(--slate-300)', borderRadius: 'var(--radius-md)' }}>
            <p style={{ color: 'var(--slate-600)', marginBottom: '10px' }}>No listings created yet.</p>
            <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
              <PlusCircle size={16} /> Create First Listing
            </button>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Farmer / Contributor</th>
                  <th>Crop & Grade</th>
                  <th>Available / Total</th>
                  <th>Location</th>
                  <th>Remaining Shelf Life</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((l) => {
                  const cropName = typeof l.crop === 'object' ? l.crop.name : l.crop;
                  const farmerName = l.farmer?.user?.full_name || 'Ravi Kumar';
                  const shelfHours = parseFloat(l.remaining_shelf_life_hours || '10.00');
                  const isExpiring = shelfHours <= 12;

                  return (
                    <tr key={l.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--slate-900)' }}>{farmerName}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>{l.self_delivery ? 'Self-delivery capable' : 'Hub pickup required'}</div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '1.1rem' }}>{cropName === 'Tomato' ? '🍅' : cropName === 'Banana' ? '🍌' : '🥦'}</span>
                          <div>
                            <strong>{cropName}</strong>
                            <span className="badge badge-neutral" style={{ marginLeft: '6px' }}>Grade {l.grade}</span>
                          </div>
                        </div>
                      </td>
                      <td className="tabular">
                        <strong>{l.available_kg} kg</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>of {l.quantity_kg} kg</div>
                      </td>
                      <td>
                        <div>{l.village}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>{l.district}</div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Clock size={14} color={isExpiring ? 'var(--amber-600)' : 'var(--primary-600)'} />
                          <span className={`tabular font-bold ${isExpiring ? 'text-amber-700' : 'text-slate-800'}`} style={{ fontWeight: 700 }}>
                            {shelfHours.toFixed(1)} hours
                          </span>
                        </div>
                        {isExpiring && (
                          <div style={{ fontSize: '0.7rem', color: 'var(--amber-700)', fontWeight: 600 }}>
                            Excludes Chennai (&gt;13h transit)
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${l.status === 'ACTIVE' ? 'badge-success' : l.status === 'RESERVED' ? 'badge-warning' : 'badge-neutral'}`}>
                          {l.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 3-Step Create Listing Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', borderBottom: '1px solid var(--slate-100)', paddingBottom: '14px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--slate-900)' }}>List Harvested Produce</h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>Step {step} of 3: {step === 1 ? 'Crop & Grade' : step === 2 ? 'Quantity & Details' : 'Price Intelligence'}</p>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowCreateModal(false)}>✕</button>
            </div>

            {/* Stepper indicator */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
              <div style={{ flex: 1, height: '4px', borderRadius: '2px', background: step >= 1 ? 'var(--primary-600)' : 'var(--slate-200)' }} />
              <div style={{ flex: 1, height: '4px', borderRadius: '2px', background: step >= 2 ? 'var(--primary-600)' : 'var(--slate-200)' }} />
              <div style={{ flex: 1, height: '4px', borderRadius: '2px', background: step >= 3 ? 'var(--primary-600)' : 'var(--slate-200)' }} />
            </div>

            {/* Step 1: Crop & Grade */}
            {step === 1 && (
              <div>
                <div className="form-group">
                  <label className="form-label">Select Crop</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                    {crops.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setSelectedCrop(c.id)}
                        style={{
                          padding: '12px',
                          borderRadius: 'var(--radius-md)',
                          border: selectedCrop === c.id ? '2px solid var(--primary-600)' : '1px solid var(--slate-300)',
                          background: selectedCrop === c.id ? 'var(--primary-50)' : '#ffffff',
                          cursor: 'pointer',
                          textAlign: 'center',
                        }}
                      >
                        <div style={{ fontSize: '1.5rem', marginBottom: '4px' }}>
                          {c.name === 'Tomato' ? '🍅' : c.name === 'Brinjal' ? '🍆' : c.name === 'Green Chilli' ? '🌶️' : c.name === 'Banana' ? '🍌' : '🧅'}
                        </div>
                        <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{c.name}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>Life: {c.usable_life_hours}h</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="form-group" style={{ marginTop: '16px' }}>
                  <label className="form-label">Quality Grade</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                    {(['A', 'B', 'C'] as const).map((g) => (
                      <button
                        key={g}
                        type="button"
                        onClick={() => setSelectedGrade(g)}
                        style={{
                          padding: '12px',
                          borderRadius: 'var(--radius-md)',
                          border: selectedGrade === g ? '2px solid var(--primary-600)' : '1px solid var(--slate-300)',
                          background: selectedGrade === g ? 'var(--primary-50)' : '#ffffff',
                          cursor: 'pointer',
                          textAlign: 'left',
                        }}
                      >
                        <div style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--slate-900)' }}>Grade {g}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)', marginTop: '2px' }}>
                          {g === 'A' ? 'Premium / Retail (1.00x)' : g === 'B' ? 'Secondary / Hotels (0.80x)' : 'Processing / Pulp (0.65x)'}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '24px' }}>
                  <button className="btn btn-primary" onClick={() => setStep(2)}>
                    Next: Quantity & Location <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Quantity & Harvest Time */}
            {step === 2 && (
              <div>
                <div className="form-group">
                  <label className="form-label">Quantity Available (kg)</label>
                  <input
                    type="number"
                    className="input tabular"
                    value={quantityKg}
                    onChange={(e) => setQuantityKg(e.target.value)}
                    placeholder="e.g. 150"
                  />
                  <span className="form-hint">Minimum 10 kg, Maximum 50,000 kg</span>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Village / Location</label>
                    <input
                      type="text"
                      className="input"
                      value={village}
                      onChange={(e) => setVillage(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">District</label>
                    <select
                      className="select"
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                    >
                      {regions.map((r) => (
                        <option key={r.id} value={r.name}>{r.name} ({r.district})</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Hours Elapsed Since Harvest</label>
                  <input
                    type="number"
                    className="input tabular"
                    value={harvestHoursAgo}
                    onChange={(e) => setHarvestHoursAgo(parseInt(e.target.value) || 0)}
                  />
                  <span className="form-hint">
                    Demo default: 26 hours ago (Leaves exactly 10 hours remaining shelf-life for 36h tomato)
                  </span>
                </div>

                <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '10px' }}>
                  <input
                    type="checkbox"
                    id="self_delivery"
                    checked={selfDelivery}
                    onChange={(e) => setSelfDelivery(e.target.checked)}
                    style={{ width: '16px', height: '16px' }}
                  />
                  <label htmlFor="self_delivery" style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--slate-800)' }}>
                    I will self-deliver directly to Cumbum Collection Centre (Saves collection fee)
                  </label>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
                  <button className="btn btn-secondary" onClick={() => setStep(1)}>Back</button>
                  <button className="btn btn-primary" onClick={handleFetchRecommendation} disabled={loadingRec}>
                    {loadingRec ? 'Analyzing Price...' : 'Get Price Intelligence'} <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Real-Time Price Intelligence */}
            {step === 3 && recommendation && (
              <div>
                <div style={{
                  background: 'linear-gradient(135deg, var(--primary-50) 0%, #ffffff 100%)',
                  border: '1px solid var(--primary-200)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                  marginBottom: '20px',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <ShieldCheck size={20} color="var(--primary-700)" />
                      <span style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--primary-900)' }}>
                        Price Intelligence Card
                      </span>
                    </div>
                    <span className="badge badge-success">Confidence: {recommendation.confidence_pct}%</span>
                  </div>

                  {/* Floor & Recommended Grid */}
                  <div className="grid-2" style={{ marginBottom: '16px' }}>
                    <div style={{ background: '#ffffff', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                        Your Protected Floor (F)
                      </div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary-800)' }} className="tabular">
                        ₹{recommendation.floor_price}/kg
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>
                        Guaranteed minimum under D1 §4 formula
                      </div>
                    </div>

                    <div style={{ background: '#ffffff', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                        Recommended Range
                      </div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--slate-900)' }} className="tabular">
                        ₹{recommendation.price_range[0]} - ₹{recommendation.price_range[1]}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>
                        Optimal matching target for bulk buyers
                      </div>
                    </div>
                  </div>

                  {/* Mandi Benchmark comparison */}
                  <div style={{ fontSize: '0.8rem', color: 'var(--slate-700)', marginBottom: '14px', padding: '8px 12px', background: 'rgba(255,255,255,0.7)', borderRadius: 'var(--radius-sm)' }}>
                    Mandi Benchmark: <strong className="tabular">₹{recommendation.mandi_benchmark}/kg</strong> • Traditional net realization (~60%): <strong className="tabular">₹{(parseFloat(recommendation.mandi_benchmark) * 0.6).toFixed(2)}/kg</strong>
                  </div>

                  {/* Why this price? Explainability payload */}
                  <div>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--slate-900)', marginBottom: '6px' }}>
                      Why this price? (Transparent Signal Breakdown)
                    </div>
                    <ul style={{ paddingLeft: '18px', fontSize: '0.78rem', color: 'var(--slate-700)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {recommendation.explanation_bullets?.map((bullet, idx) => (
                        <li key={idx}>{bullet}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <button className="btn btn-secondary" onClick={() => setStep(2)}>Back</button>
                  <button className="btn btn-primary" onClick={handlePublishListing} disabled={publishing}>
                    {publishing ? 'Publishing...' : 'Publish Listing'} <CheckCircle2 size={16} />
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>
      )}

    </div>
  );
};
