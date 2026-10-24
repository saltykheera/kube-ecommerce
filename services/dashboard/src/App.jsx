import React, { useState, useEffect } from 'react';
import { api, authStorage } from './api';
import Navbar from './components/Navbar';
import Login from './components/Login';
import ServersView from './components/ServersView';
import ToolsView from './components/ToolsView';
import KeysView from './components/KeysView';
import AuditView from './components/AuditView';
import ChatView from './components/ChatView';

export default function App() {
  const [user, setUser] = useState(authStorage.getUser());
  const [activeTab, setActiveTab] = useState('servers');

  useEffect(() => {
    const handleAuthChange = () => {
      setUser(authStorage.getUser());
    };
    window.addEventListener('auth-change', handleAuthChange);
    return () => window.removeEventListener('auth-change', handleAuthChange);
  }, []);

  const handleLogout = () => {
    api.logout();
    setUser(null);
  };

  if (!user) {
    return <Login onLoginSuccess={() => setUser(authStorage.getUser())} />;
  }

  return (
    <div className="app-container" id="app-root">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onLogout={handleLogout}
      />

      <main className="main-content">
        {activeTab === 'servers' && <ServersView user={user} />}
        {activeTab === 'tools' && <ToolsView user={user} />}
        {activeTab === 'keys' && <KeysView user={user} />}
        {activeTab === 'audit' && <AuditView user={user} />}
        {activeTab === 'chat' && <ChatView user={user} />}
      </main>
    </div>
  );
}
