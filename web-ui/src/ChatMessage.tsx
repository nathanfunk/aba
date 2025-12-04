import type { Message, ToolCall } from './useWebSocket';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <div
      className={`message ${isUser ? 'user' : isSystem ? 'system' : 'agent'}`}
    >
      <div className="message-content">{message.content}</div>
    </div>
  );
}

interface ToolCallDisplayProps {
  tools: ToolCall[];
}

export function ToolCallDisplay({ tools }: ToolCallDisplayProps) {
  if (tools.length === 0) return null;

  return (
    <div className="tool-calls">
      {tools.map((tool, idx) => (
        <div key={idx} className="tool-call">
          <div className="tool-name">🔧 {tool.name}</div>
          {tool.result !== undefined && (
            <div className={`tool-result ${tool.success ? 'success' : 'error'}`}>
              {tool.success ? '✓' : '✗'} {tool.result.substring(0, 100)}
              {tool.result.length > 100 ? '...' : ''}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
