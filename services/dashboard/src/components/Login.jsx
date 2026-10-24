import React, { useState } from 'react';
import { api } from '../api';
import { ArrowRight, ShieldCheck, UserCheck } from 'lucide-react';
import HedgehogMascot from './HedgehogMascot';

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('admin@ecommerce.local');
  const [password, setPassword] = useState('AdminSecurePassword123!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login(email, password);
      onLoginSuccess();
    } catch (err) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const setQuickUser = (role) => {
    if (role === 'admin') {
      setEmail('admin@ecommerce.local');
      setPassword('AdminSecurePassword123!');
    } else {
      setEmail('member@ecommerce.local');
      setPassword('MemberSecurePassword123!');
    }
    setError('');
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        backgroundColor: 'var(--canvas)',
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '440px',
          padding: '32px',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ marginBottom: '12px' }}>
            <HedgehogMascot pose="terminal" size={64} />
          </div>
          <div className="section-eyebrow">CLUSTER AUTHENTICATION</div>
          <h2 style={{ fontSize: '24px', fontWeight: '800', letterSpacing: '-0.6px', marginBottom: '6px' }}>
            Team MCP Gateway
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--mute)' }}>
            Sign in to access upstream servers, tool catalog, API keys, & AI agent
          </p>
        </div>

        {error && (
          <div className="callout-banner callout-red" style={{ marginBottom: '20px' }}>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: '700',
                textTransform: 'uppercase',
                color: 'var(--ink)',
                marginBottom: '6px',
                letterSpacing: '0.05em',
              }}
            >
              Email Address
            </label>
            <input
              id="input-login-email"
              type="email"
              className="input-field"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@ecommerce.local"
              required
            />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: '700',
                textTransform: 'uppercase',
                color: 'var(--ink)',
                marginBottom: '6px',
                letterSpacing: '0.05em',
              }}
            >
              Password
            </label>
            <input
              id="input-login-password"
              type="password"
              className="input-field"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
          </div>

          <button
            id="btn-login-submit"
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', height: '42px', fontSize: '15px' }}
            disabled={loading}
          >
            <span>{loading ? 'Authenticating...' : 'Sign In to Gateway'}</span>
            <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ marginTop: '28px', borderTop: '1px solid var(--hairline-soft)', paddingTop: '20px' }}>
          <div
            style={{
              fontSize: '11px',
              color: 'var(--mute)',
              textAlign: 'center',
              marginBottom: '12px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              fontWeight: '700',
            }}
          >
            Quick Fill Demo Accounts
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <button
              id="btn-quick-admin"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setQuickUser('admin')}
              style={{ display: 'flex', flexDirection: 'column', height: 'auto', padding: '8px', alignItems: 'flex-start' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--accent-purple)', fontWeight: '700' }}>
                <ShieldCheck size={14} /> Admin
              </div>
              <span style={{ fontSize: '11px', color: 'var(--mute)' }}>Full Gateway Access</span>
            </button>

            <button
              id="btn-quick-member"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setQuickUser('member')}
              style={{ display: 'flex', flexDirection: 'column', height: 'auto', padding: '8px', alignItems: 'flex-start' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--link-blue)', fontWeight: '700' }}>
                <UserCheck size={14} /> Member
              </div>
              <span style={{ fontSize: '11px', color: 'var(--mute)' }}>Read & Calc (RBAC)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
