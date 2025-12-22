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
      {message.tools && message.tools.length > 0 && (
        <ToolCallDisplay tools={message.tools} />
      )}
      {message.content && <div className="message-content">{message.content}</div>}
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
          {Object.keys(tool.arguments).length > 0 && (
            <div className="tool-arguments">
              {Object.entries(tool.arguments).map(([key, value]) => (
                <div key={key} className="tool-arg">
                  <span className="arg-name">{key}:</span>{' '}
                  <span className="arg-value">
                    {typeof value === 'string' ? value : JSON.stringify(value)}
                  </span>
                </div>
              ))}
            </div>
          )}
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
