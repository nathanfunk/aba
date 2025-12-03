import { useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { ChatMessage, ToolCallDisplay } from './ChatMessage';
import { ChatInput } from './ChatInput';
import './App.css';

function App() {
  const { messages, isConnected, isStreaming, currentToolCalls, sendMessage } =
    useWebSocket('agent-builder');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="app">
      <div className="header">
        <h1>🤖 Agent Builder</h1>
        <div className="status">
          {isConnected ? (
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
        {currentToolCalls.length > 0 && (
          <ToolCallDisplay tools={currentToolCalls} />
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <ChatInput onSend={sendMessage} disabled={!isConnected || isStreaming} />
      </div>
    </div>
  );
}

export default App;
