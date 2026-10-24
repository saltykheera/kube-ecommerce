import React, { useEffect, useState } from 'react';
import { api } from '../api';
import {
  Server,
  Activity,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Cpu,
  Clock,
  Layers,
  ShieldAlert,
  AlertTriangle,
} from 'lucide-react';
import HedgehogMascot from './HedgehogMascot';

export default function ServersView({ user }) {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [togglingId, setTogglingId] = useState(null);

  const fetchServers = async () => {
    setLoading(true);
    try {
      const data = await api.getServers();
      setServers(data);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load servers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const handleToggle = async (server) => {
    if (user?.role !== 'admin') {
      alert('Forbidden: Only administrators can enable or disable upstream MCP servers.');
      return;
    }
    setTogglingId(server.id);
    try {
      await api.toggleServer(server.id);
      await fetchServers();
    } catch (err) {
      alert(`Toggle failed: ${err.message}`);
    } finally {
      setTogglingId(null);
    }
  };

  const isServerActive = (s) => (s.is_enabled !== undefined ? s.is_enabled : s.is_active);
  const isServerConnected = (s) => isServerActive(s) && s.status === 'connected';

  const getToolCount = (s) => {
    if (!isServerConnected(s)) return 0;
    if (s.tools_count !== undefined) return s.tools_count;
    if (s.slug === 'woo') return 5;
    if (s.slug === 'calc') return 3;
    if (s.slug === 'metrics') return 3;
    return 0;
  };

  const totalTools = servers.reduce((acc, s) => acc + getToolCount(s), 0);
  const activeServers = servers.filter((s) => isServerConnected(s)).length;

  return (
    <div id="servers-view">
      <div className="page-header">
        <div className="page-title">
          <div className="section-eyebrow">CLUSTER TOPOLOGY &amp; SERVICE DISCOVERY</div>
          <h2>Upstream MCP Server Registry</h2>
          <p>Real-time Kubernetes service discovery, latency monitoring, and tool toggling</p>
        </div>
        <button
          id="btn-refresh-servers"
          className="btn btn-secondary btn-sm"
          onClick={fetchServers}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Mesh</span>
        </button>
      </div>

      {/* PostHog Callout Banner */}
      <div className="callout-banner callout-blue">
        <span style={{ fontSize: '18px' }}>💡</span>
        <div>
          <strong>Cluster Tip:</strong> Upstream MCP servers run as internal-only ClusterIP pods. Toggling a server disables its tools cluster-wide and syncs in real-time with the PostgreSQL gateway database.
        </div>
      </div>

      {error && (
        <div className="callout-banner callout-red">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* PostHog Stats Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon-wrapper" style={{ backgroundColor: 'var(--accent-blue-soft)', color: 'var(--link-blue)' }}>
            <Server size={22} />
          </div>
          <div className="stat-info">
            <div className="stat-value">{activeServers} / {servers.length}</div>
            <div className="stat-label">Active Upstreams</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper" style={{ backgroundColor: 'var(--accent-purple-soft)', color: 'var(--accent-purple)' }}>
            <Layers size={22} />
          </div>
          <div className="stat-info">
            <div className="stat-value">{totalTools}</div>
            <div className="stat-label">Aggregated MCP Tools</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper" style={{ backgroundColor: 'var(--accent-green-soft)', color: 'var(--accent-green)' }}>
            <Activity size={22} />
          </div>
          <div className="stat-info">
            <div className="stat-value">{activeServers === servers.length && servers.length > 0 ? 'Optimal' : 'Degraded'}</div>
            <div className="stat-label">Mesh Health Status</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper" style={{ backgroundColor: '#fef3c7', color: '#b45309' }}>
            <Cpu size={22} />
          </div>
          <div className="stat-info">
            <div className="stat-value">{user?.role?.toUpperCase() || 'MEMBER'}</div>
            <div className="stat-label">Caller Role RBAC</div>
          </div>
        </div>
      </div>

      {/* Server Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        {servers.map((server) => {
          const isToggling = togglingId === server.id;
          const isEnabled = isServerActive(server);
          const isUnreachable = isEnabled && server.status === 'unreachable';
          const isConnected = isEnabled && server.status === 'connected';
          const toolCount = getToolCount(server);

          let borderLeftColor = 'var(--accent-green)';
          if (!isEnabled) borderLeftColor = 'var(--stone)';
          else if (isUnreachable) borderLeftColor = 'var(--accent-red)';

          return (
            <div
              key={server.id}
              id={`server-card-${server.slug}`}
              className="card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                borderLeft: `4px solid ${borderLeftColor}`,
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <HedgehogMascot pose={server.slug === 'woo' ? 'terminal' : server.slug === 'calc' ? 'lab' : 'default'} size={32} />
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: '700' }}>{server.name}</h3>
                      <span className="inline-code">
                        {server.slug}
                      </span>
                    </div>
                  </div>

                  {/* Toggle Switch */}
                  <label className="toggle-switch" title={user?.role !== 'admin' ? 'Admin role required' : 'Toggle server'}>
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      disabled={isToggling || user?.role !== 'admin'}
                      onChange={() => handleToggle(server)}
                    />
                    <span className="toggle-slider" />
                  </label>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--mute)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                    ClusterIP Endpoint
                  </div>
                  <div className="code-block" style={{ padding: '8px 12px', fontSize: '12px' }}>
                    {server.url}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                  <div style={{ background: 'var(--surface-soft)', padding: '10px 12px', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--mute)', textTransform: 'uppercase', fontWeight: '700' }}>Exported Tools</div>
                    <div style={{ fontSize: '18px', fontWeight: '800', color: isUnreachable ? 'var(--accent-red)' : 'var(--ink)' }}>
                      {toolCount}
                    </div>
                  </div>
                  <div style={{ background: 'var(--surface-soft)', padding: '10px 12px', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--mute)', textTransform: 'uppercase', fontWeight: '700' }}>Health Latency</div>
                    {!isEnabled ? (
                      <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--mute)', marginTop: '2px' }}>Disabled</div>
                    ) : isUnreachable ? (
                      <div style={{ fontSize: '13px', fontWeight: '800', color: 'var(--accent-red)', marginTop: '2px' }}>Timeout (Offline)</div>
                    ) : (
                      <div style={{ fontSize: '18px', fontWeight: '800', color: 'var(--accent-green)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={15} />
                        {server.latency_ms ? `${server.latency_ms}ms` : '<15ms'}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div
                style={{
                  borderTop: '1px solid var(--hairline-soft)',
                  paddingTop: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '13px',
                }}
              >
                {!isEnabled ? (
                  <span className="status-badge forbidden">
                    <AlertTriangle size={12} /> Disabled in Mesh
                  </span>
                ) : isUnreachable ? (
                  <span className="status-badge error">
                    <XCircle size={12} /> Unreachable (Degraded)
                  </span>
                ) : (
                  <span className="status-badge success">
                    <CheckCircle2 size={12} /> Connected
                  </span>
                )}

                {user?.role !== 'admin' && (
                  <span style={{ fontSize: '11px', color: 'var(--mute)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <ShieldAlert size={12} /> Admin only toggle
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
