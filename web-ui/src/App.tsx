import { useCallback, useEffect, useRef, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { AgentSelector } from './AgentSelector';
import './App.css';

const STORAGE_KEY = 'aba-selected-agent';
const DEFAULT_AGENT = 'agent-builder';

function App() {
  const [selectedAgent, setSelectedAgent] = useState<string>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) return stored;
    } catch (error) {
      console.warn('localStorage not available:', error);
    }
    return DEFAULT_AGENT;
  });

  const [isSwitching, setIsSwitching] = useState(false);

  const { messages, isConnected, isStreaming, sendMessage, clearMessages } =
    useWebSocket(selectedAgent);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const validateAgent = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/agents/${selectedAgent}`);
        if (!response.ok) throw new Error('Agent not found');
      } catch (error) {
        console.warn(`Agent '${selectedAgent}' not found, switching to default`);
        setSelectedAgent(DEFAULT_AGENT);
        try {
          localStorage.setItem(STORAGE_KEY, DEFAULT_AGENT);
        } catch (e) {
          console.warn('Could not save to localStorage:', e);
        }
      }
    };
    validateAgent();
  }, []);

  const handleAgentChange = useCallback((newAgent: string) => {
    if (newAgent === selectedAgent) return;

    setIsSwitching(true);
    clearMessages();
    setSelectedAgent(newAgent);

    try {
      localStorage.setItem(STORAGE_KEY, newAgent);
    } catch (error) {
      console.warn('Could not save to localStorage:', error);
    }

    setTimeout(() => setIsSwitching(false), 500);
  }, [selectedAgent, clearMessages]);

  return (
    <div className="app">
      <div className="header">
        <div className="header-left">
          <h1>🤖 Agent Builder</h1>
          <AgentSelector
            selectedAgent={selectedAgent}
            onAgentChange={handleAgentChange}
            disabled={!isConnected || isStreaming || isSwitching}
          />
        </div>
        <div className="status">
          {isSwitching ? (
            <span className="switching">⟳ Switching...</span>
          ) : isConnected ? (
            <span className="connected">● Connected</span>
          ) : (
            <span className="disconnected">○ Disconnected</span>
          )}
        </div>
      </div>

      <div className="messages-container">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <ChatInput onSend={sendMessage} disabled={!isConnected || isStreaming || isSwitching} />
      </div>
    </div>
  );
}

export default App;
