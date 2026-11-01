import React, { useState } from 'react';
import { api } from '../api';
import { ArrowRight, ShieldCheck, UserCheck } from 'lucide-react';
import HedgehogMascot from './HedgehogMascot';

// Public demo credentials; cloud builds supply their own demo account values.
const DEMO_ACCOUNTS = {
  admin: {
    email: 'admin@ecommerce.local',
    password: import.meta.env.VITE_DEMO_ADMIN_PASSWORD || 'AdminSecurePassword123!',
  },
  member: {
    email: 'member@ecommerce.local',
    password: import.meta.env.VITE_DEMO_MEMBER_PASSWORD || 'MemberSecurePassword123!',
  },
};

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState(DEMO_ACCOUNTS.admin.email);
  const [password, setPassword] = useState(DEMO_ACCOUNTS.admin.password);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const demoAccount = Object.values(DEMO_ACCOUNTS).find(
    (account) => account.email === email.trim().toLowerCase(),
  );

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
    setEmail(DEMO_ACCOUNTS[role].email);
    setPassword(DEMO_ACCOUNTS[role].password);
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
              htmlFor="input-login-email"
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
              htmlFor="input-login-password"
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
              placeholder={demoAccount?.password || 'Enter your password'}
              aria-describedby={demoAccount ? 'demo-password-hint' : undefined}
              required
            />
            {demoAccount && (
              <p id="demo-password-hint" style={{ marginTop: '8px', fontSize: '12px', color: 'var(--mute)', overflowWrap: 'anywhere' }}>
                Demo password: <code>{demoAccount.password}</code>
              </p>
            )}
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
