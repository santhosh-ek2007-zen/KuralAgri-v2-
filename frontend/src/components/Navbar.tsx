import React, { useState } from 'react';
import { User, api } from '../api';
import { Sprout, ShoppingCart, ShieldCheck, RefreshCw, Globe, ChevronDown, Check } from 'lucide-react';

interface NavbarProps {
  currentUser: User | null;
  onUserChange: (user: User) => void;
  currentTab: string;
  onTabChange: (tab: string) => void;
  onResetDemo: () => void;
  isResetting: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  onUserChange,
  currentTab,
  onTabChange,
  onResetDemo,
  isResetting,
}) => {
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const [lang, setLang] = useState<'en' | 'ta'>('en');

  const demoRoles = [
    { role: 'FARMER', label: 'Farmer (Ravi Kumar)', phone: '9000000001', icon: Sprout, sub: 'Theni • 0 orders • Tier NEW' },
    { role: 'BUYER', label: 'Buyer (Theni Fresh Mart)', phone: '9100000001', icon: ShoppingCart, sub: 'Theni • Premium Buyer' },
    { role: 'ADMIN', label: 'Admin (KuralAgri Ops)', phone: '9200000000', icon: ShieldCheck, sub: 'Logistics, Routing & Escrow' },
  ];

  const handleRoleSwitch = async (phone: string) => {
    try {
      const res = await api.login(phone);
      onUserChange(res.user);
      setShowRoleMenu(false);
      if (res.user.role === 'FARMER') onTabChange('farmer_dashboard');
      else if (res.user.role === 'BUYER') onTabChange('buyer_dashboard');
      else onTabChange('admin_dashboard');
    } catch (err: any) {
      alert(`Role switch error: ${err.message}`);
    }
  };

  return (
    <header style={{ background: '#ffffff', borderBottom: '1px solid var(--slate-200)', position: 'sticky', top: 0, zIndex: 100 }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px' }}>
        
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={() => {
          if (currentUser?.role === 'FARMER') onTabChange('farmer_dashboard');
          else if (currentUser?.role === 'BUYER') onTabChange('buyer_dashboard');
          else onTabChange('admin_dashboard');
        }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, var(--primary-700), var(--primary-900))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '20px', boxShadow: 'var(--shadow-sm)' }}>
            🌾
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)', letterSpacing: '-0.03em' }}>KuralAgri</span>
              <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>SIH MVP</span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)', fontWeight: 500 }}>
              {lang === 'en' ? 'குரல் அக்ரி • Fair Agri Intelligence & Settlement' : 'நியாயமான விலை மற்றும் உடனடி முன்பணம்'}
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {currentUser?.role === 'FARMER' && (
            <>
              <button 
                className={`btn ${currentTab === 'farmer_dashboard' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onTabChange('farmer_dashboard')}
              >
                🌾 My Produce & Earnings
              </button>
              <button 
                className={`btn ${currentTab === 'market_intelligence' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onTabChange('market_intelligence')}
              >
                📊 Market Intelligence
              </button>
            </>
          )}

          {currentUser?.role === 'BUYER' && (
            <>
              <button 
                className={`btn ${currentTab === 'buyer_dashboard' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onTabChange('buyer_dashboard')}
              >
                🏢 Orders & Lots
              </button>
              <button 
                className={`btn ${currentTab === 'market_intelligence' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onTabChange('market_intelligence')}
              >
                📊 Price Trends
              </button>
            </>
          )}

          {currentUser?.role === 'ADMIN' && (
            <>
              <button 
                className={`btn ${currentTab === 'admin_dashboard' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onTabChange('admin_dashboard')}
              >
                ⚙️ Ops Overview
              </button>
              <button 
                className={`btn ${currentTab === 'logistics_planner' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onTabChange('logistics_planner')}
              >
                🚚 Logistics & CVRP Route
              </button>
              <button 
                className={`btn ${currentTab === 'rejection_recovery' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onTabChange('rejection_recovery')}
              >
                ♻️ Anti-Waste Recovery
              </button>
              <button 
                className={`btn ${currentTab === 'market_intelligence' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onTabChange('market_intelligence')}
              >
                📊 Market Signals
              </button>
            </>
          )}
        </nav>

        {/* Right Tools: Role Switcher, Reset Demo, Language */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          
          {/* Quick Role Switcher */}
          <div style={{ position: 'relative' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setShowRoleMenu(!showRoleMenu)}
              style={{ padding: '6px 12px', borderColor: 'var(--primary-600)', background: 'var(--primary-50)' }}
            >
              <span style={{ fontSize: '0.8rem', color: 'var(--primary-800)', fontWeight: 600 }}>
                Role: <strong>{currentUser?.role || 'Switch'}</strong> ({currentUser?.full_name?.split(' ')[0] || ''})
              </span>
              <ChevronDown size={14} color="var(--primary-800)" />
            </button>

            {showRoleMenu && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '8px',
                background: '#ffffff',
                border: '1px solid var(--slate-200)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-xl)',
                width: '300px',
                zIndex: 200,
                padding: '8px',
              }}>
                <div style={{ padding: '8px 12px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--slate-400)', textTransform: 'uppercase' }}>
                  Demo Presentation Roles (§16)
                </div>
                {demoRoles.map((dr) => {
                  const Icon = dr.icon;
                  const isCurrent = currentUser?.role === dr.role;
                  return (
                    <div
                      key={dr.phone}
                      onClick={() => handleRoleSwitch(dr.phone)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: isCurrent ? 'var(--primary-50)' : 'transparent',
                        transition: 'background 0.1s ease',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = isCurrent ? 'var(--primary-50)' : 'var(--slate-50)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = isCurrent ? 'var(--primary-50)' : 'transparent'}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                          width: '32px', height: '32px', borderRadius: '8px',
                          background: isCurrent ? 'var(--primary-600)' : 'var(--slate-100)',
                          color: isCurrent ? '#ffffff' : 'var(--slate-700)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}>
                          <Icon size={16} />
                        </div>
                        <div>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--slate-900)' }}>{dr.label}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--slate-500)' }}>{dr.sub}</div>
                        </div>
                      </div>
                      {isCurrent && <Check size={16} color="var(--primary-600)" />}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Reset Demo Button */}
          <button
            className="btn btn-secondary btn-sm"
            onClick={onResetDemo}
            disabled={isResetting}
            title="Reset database to pristine §16 demo state"
            style={{ color: 'var(--amber-700)', borderColor: 'var(--amber-300)', background: 'var(--amber-50)' }}
          >
            <RefreshCw size={13} className={isResetting ? 'spin' : ''} />
            {isResetting ? 'Resetting...' : 'Reset Demo'}
          </button>

          {/* Language Toggle */}
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setLang(lang === 'en' ? 'ta' : 'en')}
            style={{ padding: '6px 10px' }}
          >
            <Globe size={13} />
            {lang === 'en' ? 'தமிழ்' : 'English'}
          </button>
        </div>
      </div>
    </header>
  );
};
