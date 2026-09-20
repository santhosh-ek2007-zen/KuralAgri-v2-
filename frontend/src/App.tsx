import React, { useState, useEffect } from 'react';
import { User, api } from './api';
import { Navbar } from './components/Navbar';
import { FarmerView } from './components/FarmerView';
import { BuyerView } from './components/BuyerView';
import { AdminView } from './components/AdminView';
import { MarketIntelligenceView } from './components/MarketIntelligenceView';

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentTab, setCurrentTab] = useState<string>('farmer_dashboard');
  const [isResetting, setIsResetting] = useState(false);
  const [initLoading, setInitLoading] = useState(true);

  // Initialize with demo user (Ravi Kumar - Farmer)
  useEffect(() => {
    initAuth();
  }, []);

  const initAuth = async () => {
    try {
      // Try existing session or auto-login with primary demo farmer
      try {
        const me = await api.getMe();
        setCurrentUser(me);
        if (me.role === 'FARMER') setCurrentTab('farmer_dashboard');
        else if (me.role === 'BUYER') setCurrentTab('buyer_dashboard');
        else setCurrentTab('admin_dashboard');
      } catch {
        const loginRes = await api.login('9000000001', 'Demo@1234');
        setCurrentUser(loginRes.user);
        setCurrentTab('farmer_dashboard');
      }
    } catch (err) {
      console.error('Initial login error:', err);
    } finally {
      setInitLoading(false);
    }
  };

  const handleResetDemo = async () => {
    if (!window.confirm("Are you sure you want to reset demo data? This will restore all §16 tables to their initial demo state.")) {
      return;
    }
    try {
      setIsResetting(true);
      const res = await api.resetDemoData();
      alert(res.message || "Demo data restored successfully.");
      window.location.reload();
    } catch (err: any) {
      alert(`Reset error: ${err.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  if (initLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>🌾</div>
          <h2 style={{ fontSize: '1.25rem', color: 'var(--slate-800)' }}>Initializing KuralAgri Demo...</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--slate-500)', marginTop: '4px' }}>Loading §16 Seed Dataset & Models</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f8fafc' }}>
      {/* Top sticky navigation */}
      <Navbar
        currentUser={currentUser}
        onUserChange={setCurrentUser}
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
      />

      {/* Main content body */}
      <main style={{ flex: 1 }}>
        {currentTab === 'farmer_dashboard' && <FarmerView />}
        {currentTab === 'buyer_dashboard' && <BuyerView />}
        {(currentTab === 'admin_dashboard' || currentTab === 'logistics_planner' || currentTab === 'rejection_recovery') && (
          <AdminView currentTab={currentTab} onTabChange={setCurrentTab} />
        )}
        {currentTab === 'market_intelligence' && <MarketIntelligenceView />}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--slate-200)', background: '#ffffff', padding: '20px 24px', marginTop: '40px' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', fontSize: '0.8rem', color: 'var(--slate-500)' }}>
          <div>
            <strong>KuralAgri MVP</strong> • Smart India Hackathon Prototype • Asset-Light Produce Destination, Pricing & Settlement Marketplace
          </div>
          <div>
            Built with Django 5 + PostgreSQL 16 + React 18 & Leaflet • All rates bound by §16.1 table parameters
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
