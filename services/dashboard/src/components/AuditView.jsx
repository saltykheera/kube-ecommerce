import React, { useEffect, useState } from 'react';
import { api } from '../api';
import {
  ShieldCheck,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Code2,
  X,
  User,
} from 'lucide-react';
import HedgehogMascot from './HedgehogMascot';

export default function AuditView({ user }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs({
        limit: 100,
        status: statusFilter,
      });
      setLogs(data);
    } catch (err) {
      console.error('Error fetching audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [statusFilter]);

  const filteredLogs = logs.filter((log) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (log.tool_name && log.tool_name.toLowerCase().includes(term)) ||
      (log.user_email && log.user_email.toLowerCase().includes(term)) ||
      (log.server_slug && log.server_slug.toLowerCase().includes(term))
    );
  });

  const getStatusBadge = (status) => {
    if (status === 'success') {
      return (
        <span className="status-badge success">
          <CheckCircle2 size={11} /> SUCCESS
        </span>
      );
    }
    if (status === 'forbidden') {
      return (
        <span className="status-badge forbidden">
          <AlertTriangle size={11} /> FORBIDDEN
        </span>
      );
    }
    return (
      <span className="status-badge error">
        <XCircle size={11} /> ERROR
      </span>
    );
  };

  return (
    <div id="audit-view">
      <div className="page-header">
        <div className="page-title">
          <div className="section-eyebrow">CLUSTER AUDIT LOGGING</div>
          <h2>Security &amp; Tool Execution Audit Trail</h2>
          <p>Immutable PostgreSQL logging for every MCP tool call with RBAC enforcement tracking</p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', minWidth: '240px' }}>
            <Search
              size={15}
              style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--mute)' }}
            />
            <input
              id="input-audit-search"
              type="text"
              className="input-field"
              style={{ paddingLeft: '32px' }}
              placeholder="Search by tool or caller..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="nav-tabs" style={{ padding: '2px' }}>
            {[
              { id: 'all', label: 'All' },
              { id: 'success', label: 'Success' },
              { id: 'forbidden', label: 'Forbidden' },
              { id: 'error', label: 'Errors' },
            ].map((f) => (
              <button
                key={f.id}
                id={`audit-filter-${f.id}`}
                className={`nav-tab-btn ${statusFilter === f.id ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setStatusFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>

          <button
            id="btn-refresh-audit"
            className="btn btn-secondary btn-sm"
            onClick={fetchLogs}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="callout-banner callout-blue" style={{ marginBottom: '20px' }}>
        <span>💡</span>
        <div>
          <strong>PostgreSQL Audit Retention:</strong> Every tool execution records execution duration, caller email, API key ID, and response status. Blocked actions record the exact RBAC violation.
        </div>
      </div>

      {/* Audit Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-responsive">
          <table className="custom-table" id="audit-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Caller Identity</th>
                <th>Server Slug</th>
                <th>Tool Name</th>
                <th>Status</th>
                <th>Duration</th>
                <th style={{ textAlign: 'right' }}>Payload</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--mute)' }}>
                    No audit records match the current filter.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} id={`audit-row-${log.id}`}>
                    <td style={{ color: 'var(--body)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <Clock size={12} style={{ color: 'var(--mute)' }} />
                        {new Date(log.created_at).toLocaleTimeString()} ({new Date(log.created_at).toLocaleDateString()})
                      </div>
                    </td>

                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <User size={13} style={{ color: 'var(--mute)' }} />
                        <span style={{ fontSize: '13px', color: 'var(--ink)', fontWeight: '600' }}>
                          {log.user_email || `User #${log.user_id}`}
                        </span>
                      </div>
                    </td>

                    <td>
                      <span className="inline-code">
                        {log.server_slug}
                      </span>
                    </td>

                    <td>
                      <code style={{ fontSize: '13px', color: 'var(--ink)', fontWeight: '600' }}>
                        {log.tool_name}
                      </code>
                    </td>

                    <td>{getStatusBadge(log.status)}</td>

                    <td style={{ fontSize: '13px', color: 'var(--mute)', fontFamily: 'var(--font-mono)' }}>
                      {log.duration_ms ? `${log.duration_ms}ms` : '—'}
                    </td>

                    <td style={{ textAlign: 'right' }}>
                      <button
                        id={`btn-view-audit-${log.id}`}
                        className="btn btn-secondary btn-sm"
                        onClick={() => setSelectedLog(log)}
                      >
                        <Code2 size={13} /> View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Inspect Log Details Modal */}
      {selectedLog && (
        <div className="modal-backdrop" onClick={() => setSelectedLog(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} style={{ color: 'var(--ink)' }} />
                <h3 style={{ fontSize: '16px' }}>Audit Log Record #{selectedLog.id}</h3>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setSelectedLog(null)}
                style={{ padding: '2px 6px', height: '28px' }}
              >
                <X size={15} />
              </button>
            </div>

            <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '16px' }}>
                <div style={{ backgroundColor: 'var(--surface-soft)', padding: '10px 12px', borderRadius: 'var(--radius-sm)' }}>
                  <div className="section-eyebrow">CALLER EMAIL</div>
                  <div style={{ fontSize: '13px', color: 'var(--ink)', fontWeight: '600' }}>{selectedLog.user_email}</div>
                </div>
                <div style={{ backgroundColor: 'var(--surface-soft)', padding: '10px 12px', borderRadius: 'var(--radius-sm)' }}>
                  <div className="section-eyebrow">STATUS</div>
                  <div style={{ marginTop: '2px' }}>{getStatusBadge(selectedLog.status)}</div>
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <div className="section-eyebrow">ARGUMENTS PASSED TO MCP UPSTREAM</div>
                <div className="code-block" style={{ maxHeight: '180px' }}>
                  <pre>
                    {(() => {
                      try {
                        return JSON.stringify(JSON.parse(selectedLog.arguments || '{}'), null, 2);
                      } catch {
                        return selectedLog.arguments || '{}';
                      }
                    })()}
                  </pre>
                </div>
              </div>

              {selectedLog.error_message && (
                <div>
                  <div className="section-eyebrow">ERROR / RBAC REJECTION MESSAGE</div>
                  <div className="callout-banner callout-red" style={{ margin: 0 }}>
                    <span>⚠️</span>
                    <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {selectedLog.error_message}
                    </pre>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedLog(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
