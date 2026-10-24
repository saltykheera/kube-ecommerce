import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import {
  Send,
  User,
  Wrench,
  ChevronDown,
  ChevronRight,
  Clock,
  RotateCcw,
} from 'lucide-react';
import HedgehogMascot from './HedgehogMascot';

export default function ChatView({ user }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: `Hello ${user?.email?.split('@')[0] || 'there'}! I'm your PostHog-style eCommerce AI Assistant powered by Google Gemini. I have direct access to your WooCommerce cluster tools, financial calculator, and real-time business metrics.\n\nTry asking me to list store products, calculate sales taxes, or pull revenue stats!`,
      tool_calls: [],
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedTools, setExpandedTools] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const toggleToolExpand = (index, tcIndex) => {
    const key = `${index}-${tcIndex}`;
    setExpandedTools((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleSend = async (messageText = input) => {
    const textToSend = messageText.trim();
    if (!textToSend || loading) return;

    const newMessages = [...messages, { role: 'user', text: textToSend }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const history = messages.slice(-6).map((m) => ({
        role: m.role,
        text: m.text,
      }));

      const response = await api.sendChat(textToSend, history);

      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          text: response.reply,
          tool_calls: response.tool_calls || [],
        },
      ]);
    } catch (err) {
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          text: `Error from AI Gateway: ${err.message}`,
          tool_calls: [],
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const starterPrompts = [
    { label: '📦 List Store Products', prompt: 'List the current products available in our WooCommerce store.' },
    { label: '🧮 Calculate 10% Tax on $150', prompt: 'Calculate a 10% sales tax on a $150 order and give me the total.' },
    { label: '📈 Store Revenue Summary', prompt: 'Provide a complete summary of store revenue and order metrics.' },
    { label: '➕ Create Product (Admin/RBAC)', prompt: 'Create a new product named Cyber Hoodie priced at $89.99 in WooCommerce.' },
  ];

  return (
    <div id="chat-view">
      <div className="page-header" style={{ marginBottom: '16px' }}>
        <div className="page-title">
          <div className="section-eyebrow">GEMINI TOOL-CALLING ORCHESTRATION</div>
          <h2>Ask MCP Agent</h2>
          <p>
            Autonomous multi-turn agent executing MCP tools under your active identity ({user?.email}) with full RBAC enforcement
          </p>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={() =>
            setMessages([
              {
                role: 'assistant',
                text: "Chat history cleared. How can I assist you with your store operations?",
                tool_calls: [],
              },
            ])
          }
        >
          <RotateCcw size={14} /> Clear History
        </button>
      </div>

      <div className="chat-container">
        {/* Chat Header */}
        <div className="chat-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <HedgehogMascot pose="lab" size={32} />
            <div>
              <div style={{ fontWeight: '700', fontSize: '14px', color: 'var(--ink)' }}>
                Gemini 2.x Autonomous Agent
              </div>
              <div style={{ fontSize: '12px', color: 'var(--mute)' }}>
                11 MCP tools attached • Authenticated caller: <strong style={{ color: 'var(--ink)' }}>{user?.email}</strong>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="pulse-dot" />
            <span style={{ fontSize: '12px', color: 'var(--accent-green)', fontWeight: '700' }}>Active</span>
          </div>
        </div>

        {/* Message Stream */}
        <div className="chat-messages" id="chat-messages-container">
          {messages.map((m, idx) => {
            const isUser = m.role === 'user';
            return (
              <div
                key={idx}
                className={`message-bubble ${isUser ? 'user' : 'assistant'}`}
                id={`chat-msg-${idx}`}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--mute)' }}>
                  {isUser ? (
                    <>
                      <User size={13} />
                      <span>You</span>
                    </>
                  ) : (
                    <>
                      <HedgehogMascot pose="default" size={16} />
                      <span style={{ fontWeight: '600', color: 'var(--ink)' }}>MCP Assistant</span>
                    </>
                  )}
                </div>

                {/* Render Executed Tool Calls */}
                {m.tool_calls && m.tool_calls.length > 0 && (
                  <div style={{ marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {m.tool_calls.map((tc, tcIdx) => {
                      const isExpanded = !!expandedTools[`${idx}-${tcIdx}`];
                      const isSuccess = tc.status === 'success';
                      return (
                        <div key={tcIdx} className="tool-chip">
                          <div
                            className="tool-chip-header"
                            onClick={() => toggleToolExpand(idx, tcIdx)}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <Wrench size={13} />
                              <span style={{ color: 'var(--ink)' }}>Tool: {tc.tool}</span>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ fontSize: '11px', color: 'var(--mute)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                                <Clock size={11} /> {tc.duration_ms ? `${tc.duration_ms}ms` : '—'}
                              </span>
                              <span className={`status-badge ${isSuccess ? 'success' : 'forbidden'}`}>
                                {tc.status?.toUpperCase() || 'CALLED'}
                              </span>
                              {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            </div>
                          </div>

                          {isExpanded && (
                            <div style={{ marginTop: '8px', borderTop: '1px solid var(--hairline-soft)', paddingTop: '8px' }}>
                              <div className="section-eyebrow">ARGUMENTS</div>
                              <div className="code-block" style={{ padding: '8px 12px', fontSize: '12px', marginBottom: '8px' }}>
                                <pre>{JSON.stringify(tc.arguments || {}, null, 2)}</pre>
                              </div>

                              <div className="section-eyebrow">EXECUTION RESULT</div>
                              <div className="code-block" style={{ padding: '8px 12px', fontSize: '12px', maxHeight: '160px' }}>
                                <pre>{JSON.stringify(tc.result || {}, null, 2)}</pre>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                <div
                  className="bubble-content"
                  style={{
                    whiteSpace: 'pre-wrap',
                    backgroundColor: m.isError ? 'var(--accent-red-soft)' : undefined,
                    color: m.isError ? 'var(--accent-red)' : undefined,
                  }}
                >
                  {m.text}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="message-bubble assistant">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--mute)' }}>
                <HedgehogMascot pose="lab" size={16} />
                <span style={{ fontWeight: '600', color: 'var(--ink)' }}>Agent Thinking</span>
              </div>
              <div className="bubble-content" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="pulse-dot" style={{ backgroundColor: 'var(--primary)' }} />
                <span style={{ fontSize: '14px', color: 'var(--mute)' }}>
                  Executing MCP tool loop & synthesizing response...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Starter Prompts */}
        <div className="prompt-suggestions">
          {starterPrompts.map((sp, i) => (
            <button
              key={i}
              className="prompt-chip"
              onClick={() => handleSend(sp.prompt)}
              disabled={loading}
            >
              {sp.label}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="chat-input-bar">
          <input
            id="input-chat-message"
            type="text"
            className="input-field"
            placeholder="Ask a question or request a store action (e.g. 'What products are in WooCommerce?')..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
            disabled={loading}
          />

          <button
            id="btn-chat-send"
            className="btn btn-primary"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            <span>Send</span>
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
