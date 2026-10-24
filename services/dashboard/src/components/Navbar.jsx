import React from 'react';
import {
  Server,
  Wrench,
  Key,
  ShieldCheck,
  MessageSquareCode,
  LogOut,
} from 'lucide-react';
import HedgehogMascot from './HedgehogMascot';

export default function Navbar({ activeTab, setActiveTab, user, onLogout }) {
  const navItems = [
    { id: 'servers', label: 'Servers', icon: Server },
    { id: 'tools', label: 'Tool Catalog', icon: Wrench },
    { id: 'keys', label: 'API Keys', icon: Key },
    { id: 'audit', label: 'Audit Trail', icon: ShieldCheck },
    { id: 'chat', label: 'Ask MCP Agent', icon: MessageSquareCode, badge: 'AI' },
  ];

  return (
    <header className="header" id="main-header">
      <div className="header-brand" onClick={() => setActiveTab('servers')}>
        <HedgehogMascot pose="default" size={34} />
        <div className="brand-text">
          <h1>
            Team MCP Gateway
          </h1>
          <span>Kubernetes Cluster Mesh</span>
        </div>
      </div>

      <nav className="nav-tabs" id="nav-tabs-bar">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              id={`nav-tab-${item.id}`}
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={15} />
              <span>{item.label}</span>
              {item.badge && (
                <span
                  style={{
                    fontSize: '10px',
                    backgroundColor: isActive ? 'var(--primary)' : 'var(--hairline)',
                    color: 'var(--on-primary)',
                    padding: '1px 6px',
                    borderRadius: '999px',
                    fontWeight: '700',
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="user-nav-badge">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--ink)' }}>
            {user?.email || 'Logged In'}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginTop: '2px' }}>
            <span className="pulse-dot" />
            <span className={`role-pill ${user?.role || 'member'}`}>
              {user?.role || 'member'}
            </span>
          </div>
        </div>

        <button
          id="btn-logout"
          className="btn btn-secondary btn-sm"
          onClick={onLogout}
          title="Sign out"
        >
          <LogOut size={14} />
          <span>Sign out</span>
        </button>
      </div>
    </header>
  );
}
