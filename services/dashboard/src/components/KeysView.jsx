import React, { useEffect, useState } from 'react';
import { api } from '../api';
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Check,
  Clock,
  X,
} from 'lucide-react';
import HedgehogMascot from './HedgehogMascot';

export default function KeysView({ user }) {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [keyName, setKeyName] = useState('');
  const [newGeneratedKey, setNewGeneratedKey] = useState(null);
  const [copied, setCopied] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fetchKeys = async () => {
    setLoading(true);
    try {
      const data = await api.getKeys();
      setKeys(data);
    } catch (err) {
      console.error('Error fetching keys:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreateKey = async (e) => {
    e.preventDefault();
    if (!keyName.trim()) return;
    setSubmitting(true);
    try {
      const result = await api.createKey(keyName);
      setNewGeneratedKey(result.key);
      await fetchKeys();
      setKeyName('');
    } catch (err) {
      alert(`Failed to create key: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevoke = async (keyItem) => {
    if (!window.confirm(`Are you sure you want to permanently revoke key "${keyItem.name}"? Immediate 401 Unauthorized will be enforced.`)) {
      return;
    }
    try {
      await api.revokeKey(keyItem.id);
      await fetchKeys();
    } catch (err) {
      alert(`Revocation failed: ${err.message}`);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div id="keys-view">
      <div className="page-header">
        <div className="page-title">
          <div className="section-eyebrow">PROGRAMMATIC ACCESS CONTROL</div>
          <h2>API Key Management</h2>
          <p>Generate, monitor, and revoke SHA-256 hashed Bearer keys for MCP clients</p>
        </div>

        <button
          id="btn-open-create-key"
          className="btn btn-primary"
          onClick={() => {
            setNewGeneratedKey(null);
            setIsModalOpen(true);
          }}
        >
          <Plus size={16} />
          <span>Generate New Key</span>
        </button>
      </div>

      <div className="callout-banner callout-purple" style={{ marginBottom: '20px' }}>
        <span>📘</span>
        <div>
          <strong>Security Protocol:</strong> Keys are cryptographically hashed using SHA-256 before storage. Revoking a key invalidates it across all cluster nodes within milliseconds.
        </div>
      </div>

      {/* Keys Table Card */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-responsive">
          <table className="custom-table" id="keys-table">
            <thead>
              <tr>
                <th>Key Name</th>
                <th>Prefix Hint</th>
                <th>Created</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '40px', color: 'var(--mute)' }}>
                    No API keys found for this account. Click "Generate New Key" to create one.
                  </td>
                </tr>
              ) : (
                keys.map((k) => (
                  <tr key={k.id} id={`key-row-${k.id}`}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: 'var(--radius-sm)',
                            backgroundColor: k.is_active ? 'var(--accent-blue-soft)' : 'var(--surface-soft)',
                            color: k.is_active ? 'var(--link-blue)' : 'var(--ash)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Key size={16} />
                        </div>
                        <div>
                          <div style={{ fontWeight: '600', color: 'var(--ink)' }}>{k.name}</div>
                          <span style={{ fontSize: '11px', color: 'var(--mute)' }}>ID: {k.id}</span>
                        </div>
                      </div>
                    </td>

                    <td>
                      <span className="inline-code">
                        {k.prefix || 'mcp_***'}...
                      </span>
                    </td>

                    <td style={{ color: 'var(--body)', fontSize: '13px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <Clock size={13} style={{ color: 'var(--mute)' }} />
                        {new Date(k.created_at).toLocaleDateString()}
                      </div>
                    </td>

                    <td>
                      <span className={`status-badge ${k.is_active ? 'success' : 'error'}`}>
                        {k.is_active ? 'Active' : 'Revoked'}
                      </span>
                    </td>

                    <td style={{ textAlign: 'right' }}>
                      {k.is_active ? (
                        <button
                          id={`btn-revoke-${k.id}`}
                          className="btn btn-danger btn-sm"
                          onClick={() => handleRevoke(k)}
                        >
                          <Trash2 size={13} /> Revoke
                        </button>
                      ) : (
                        <span style={{ fontSize: '12px', color: 'var(--mute)', fontStyle: 'italic' }}>
                          Revoked
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Generate Key Modal */}
      {isModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Key size={18} style={{ color: 'var(--ink)' }} />
                <h3 style={{ fontSize: '16px' }}>{newGeneratedKey ? 'API Key Generated' : 'Generate New API Key'}</h3>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setIsModalOpen(false)}
                style={{ padding: '2px 6px', height: '28px' }}
              >
                <X size={15} />
              </button>
            </div>

            <div className="modal-body">
              {newGeneratedKey ? (
                <div>
                  <div className="callout-banner callout-red" style={{ marginBottom: '16px' }}>
                    <span>⚠️</span>
                    <span>
                      Copy this secret key right now! For security reasons, the Gateway hashes this key with SHA-256 and will never display it again.
                    </span>
                  </div>

                  <div style={{ marginBottom: '20px' }}>
                    <div className="section-eyebrow">SECRET BEARER TOKEN</div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input
                        id="input-generated-key"
                        type="text"
                        readOnly
                        value={newGeneratedKey}
                        className="input-field"
                        style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--ink)' }}
                      />
                      <button
                        id="btn-copy-generated-key"
                        className="btn btn-primary"
                        onClick={() => copyToClipboard(newGeneratedKey)}
                      >
                        {copied ? <Check size={16} /> : <Copy size={16} />}
                        <span>{copied ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleCreateKey}>
                  <div style={{ marginBottom: '16px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--ink)', marginBottom: '6px' }}>
                      Key Identifier / Name
                    </label>
                    <input
                      id="input-key-name"
                      type="text"
                      className="input-field"
                      placeholder="e.g. Production CI/CD Bot, Claude Desktop"
                      value={keyName}
                      onChange={(e) => setKeyName(e.target.value)}
                      required
                    />
                  </div>

                  <p style={{ fontSize: '13px', color: 'var(--mute)' }}>
                    Generated keys authenticate against the <span className="inline-code">/mcp</span> endpoint with the role privileges of <strong>{user?.role}</strong>.
                  </p>

                  <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setIsModalOpen(false)}
                    >
                      Cancel
                    </button>
                    <button
                      id="btn-submit-create-key"
                      type="submit"
                      className="btn btn-primary"
                      disabled={submitting}
                    >
                      {submitting ? 'Generating...' : 'Create Secret Key'}
                    </button>
                  </div>
                </form>
              )}
            </div>

            {newGeneratedKey && (
              <div className="modal-footer">
                <button
                  id="btn-done-copy-key"
                  className="btn btn-primary"
                  onClick={() => setIsModalOpen(false)}
                >
                  I have copied my key securely
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
