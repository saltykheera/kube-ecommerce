import React, { useEffect, useState } from 'react';
import { api } from '../api';
import {
  Wrench,
  Search,
  Code2,
  Lock,
  Unlock,
  X,
  FileJson,
  CheckCircle2,
} from 'lucide-react';
import HedgehogMascot from './HedgehogMascot';

export default function ToolsView({ user }) {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [serverFilter, setServerFilter] = useState('all');
  const [selectedTool, setSelectedTool] = useState(null);

  useEffect(() => {
    const fetchTools = async () => {
      setLoading(true);
      try {
        const data = await api.getTools();
        setTools(Array.isArray(data) ? data : (data.tools || []));
      } catch (err) {
        console.error('Error fetching tools:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTools();
  }, []);

  const filteredTools = tools.filter((tool) => {
    const matchesSearch =
      tool.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (tool.description && tool.description.toLowerCase().includes(searchTerm.toLowerCase()));

    if (!matchesSearch) return false;
    if (serverFilter === 'all') return true;
    return tool.name.startsWith(`${serverFilter}__`);
  });

  const isToolAdminOnly = (toolName) => {
    return ['woo__create_product', 'woo__update_order_status'].includes(toolName);
  };

  const getSlugBadge = (name) => {
    if (name.startsWith('woo__')) return { bg: 'var(--accent-purple-soft)', text: 'var(--accent-purple)' };
    if (name.startsWith('calc__')) return { bg: 'var(--accent-blue-soft)', text: 'var(--link-blue)' };
    return { bg: 'var(--accent-green-soft)', text: 'var(--accent-green)' };
  };

  return (
    <div id="tools-view">
      <div className="page-header">
        <div className="page-title">
          <div className="section-eyebrow">STANDARDIZED JSON-RPC CAPABILITIES</div>
          <h2>Aggregated MCP Tool Catalog</h2>
          <p>11 dynamically namespaced tools across WooCommerce, Calculator, and Business Metrics</p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', minWidth: '260px' }}>
            <Search
              size={15}
              style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--mute)' }}
            />
            <input
              id="input-tools-search"
              type="text"
              className="input-field"
              style={{ paddingLeft: '32px' }}
              placeholder="Search tools or parameters..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="nav-tabs" style={{ padding: '2px' }}>
            {['all', 'woo', 'calc', 'metrics'].map((f) => (
              <button
                key={f}
                id={`filter-btn-${f}`}
                className={`nav-tab-btn ${serverFilter === f ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setServerFilter(f)}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="callout-banner callout-green" style={{ marginBottom: '20px' }}>
        <span>✅</span>
        <div>
          <strong>Automatic MCP Gateway Aggregation:</strong> Upstream tools are automatically prefixed with their server slug (<span className="inline-code">woo__*</span>, <span className="inline-code">calc__*</span>, <span className="inline-code">metrics__*</span>) to avoid namespace collisions.
        </div>
      </div>

      {/* Tools Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '16px' }}>
        {filteredTools.map((tool) => {
          const adminOnly = isToolAdminOnly(tool.name);
          const slugColors = getSlugBadge(tool.name);
          const isAllowedForUser = !adminOnly || user?.role === 'admin';

          return (
            <div
              key={tool.name}
              id={`tool-card-${tool.name}`}
              className="card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                padding: '18px 20px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: '700',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: slugColors.bg,
                      color: slugColors.text,
                    }}
                  >
                    {tool.name.split('__')[0].toUpperCase()}
                  </span>

                  <span
                    className={`status-badge ${adminOnly ? 'forbidden' : 'success'}`}
                    style={{ fontSize: '10px' }}
                  >
                    {adminOnly ? <Lock size={10} /> : <Unlock size={10} />}
                    {adminOnly ? 'ADMIN ONLY' : 'ALL ROLES'}
                  </span>
                </div>

                <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-mono)', marginBottom: '6px', color: 'var(--ink)' }}>
                  {tool.name}
                </h3>

                <p style={{ fontSize: '13px', color: 'var(--body)', marginBottom: '16px', minHeight: '40px' }}>
                  {tool.description || 'No description provided by upstream service.'}
                </p>
              </div>

              <div
                style={{
                  borderTop: '1px solid var(--hairline-soft)',
                  paddingTop: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span
                  style={{
                    fontSize: '12px',
                    color: isAllowedForUser ? 'var(--accent-green)' : 'var(--mute)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontWeight: '500',
                  }}
                >
                  <CheckCircle2 size={13} />
                  {isAllowedForUser ? 'Permitted for your role' : 'Requires Admin role'}
                </span>

                <button
                  id={`btn-inspect-${tool.name}`}
                  className="btn btn-secondary btn-sm"
                  onClick={() => setSelectedTool(tool)}
                >
                  <Code2 size={13} /> Inspect Schema
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Schema Inspector Modal */}
      {selectedTool && (
        <div className="modal-backdrop" onClick={() => setSelectedTool(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileJson size={18} style={{ color: 'var(--ink)' }} />
                <h3 style={{ fontSize: '16px', fontFamily: 'var(--font-mono)' }}>
                  {selectedTool.name}
                </h3>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setSelectedTool(null)}
                style={{ padding: '2px 6px', height: '28px' }}
              >
                <X size={15} />
              </button>
            </div>

            <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
              <div style={{ marginBottom: '16px' }}>
                <div className="section-eyebrow">DESCRIPTION</div>
                <p style={{ fontSize: '14px', color: 'var(--ink)' }}>
                  {selectedTool.description}
                </p>
              </div>

              <div style={{ marginBottom: '18px' }}>
                <div className="section-eyebrow">INPUT ARGUMENTS</div>

                {selectedTool.inputSchema?.properties && Object.keys(selectedTool.inputSchema.properties).length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {Object.entries(selectedTool.inputSchema.properties).map(([propName, propDef]) => {
                      const isRequired = selectedTool.inputSchema.required?.includes(propName);
                      return (
                        <div
                          key={propName}
                          style={{
                            backgroundColor: 'var(--surface-soft)',
                            border: '1px solid var(--hairline-soft)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '10px 12px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <code style={{ color: 'var(--ink)', fontWeight: '700', fontSize: '13px' }}>
                                {propName}
                              </code>
                              <span style={{ fontSize: '12px', color: 'var(--mute)' }}>
                                ({propDef.type || 'any'})
                              </span>
                            </div>
                            {isRequired && (
                              <span style={{ fontSize: '10px', color: 'var(--accent-red)', fontWeight: '700', textTransform: 'uppercase' }}>
                                Required
                              </span>
                            )}
                          </div>
                          {propDef.description && (
                            <div style={{ fontSize: '13px', color: 'var(--body)' }}>
                              {propDef.description}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ color: 'var(--mute)', fontSize: '13px', fontStyle: 'italic' }}>
                    This tool takes no parameters.
                  </div>
                )}
              </div>

              <div>
                <div className="section-eyebrow">RAW JSON SCHEMA</div>
                <div className="code-block" style={{ maxHeight: '180px' }}>
                  <pre>{JSON.stringify(selectedTool.inputSchema || {}, null, 2)}</pre>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedTool(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
