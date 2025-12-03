import { useEffect, useRef, useState, useCallback } from 'react';

export interface Message {
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, any>;
  result?: string;
  success?: boolean;
}

interface WebSocketMessage {
  type: string;
  content?: string;
  message?: string;
  is_complete?: boolean;
  tool_name?: string;
  arguments?: Record<string, any>;
  result?: string;
  success?: boolean;
  usage?: {
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
  };
}

export function useWebSocket(agentName: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const currentMessageRef = useRef<string>('');

  useEffect(() => {
    const wsUrl = `ws://${window.location.hostname}:8000/ws/chat/${agentName}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);

      switch (data.type) {
        case 'info':
          setMessages((prev) => [
            ...prev,
            {
              role: 'system',
              content: data.message || '',
              timestamp: new Date(),
            },
          ]);
          break;

        case 'stream_chunk':
          if (data.content) {
            currentMessageRef.current += data.content;
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg && lastMsg.role === 'agent') {
                lastMsg.content = currentMessageRef.current;
                return [...newMessages];
              } else {
                return [
                  ...newMessages,
                  {
                    role: 'agent',
                    content: currentMessageRef.current,
                    timestamp: new Date(),
                  },
                ];
              }
            });
          }

          if (data.is_complete) {
            setIsStreaming(false);
            currentMessageRef.current = '';
          }
          break;

        case 'tool_start':
          setCurrentToolCalls((prev) => [
            ...prev,
            {
              name: data.tool_name || 'unknown',
              arguments: data.arguments || {},
            },
          ]);
          break;

        case 'tool_result':
          setCurrentToolCalls((prev) =>
            prev.map((tool) =>
              tool.name === data.tool_name
                ? { ...tool, result: data.result, success: data.success }
                : tool
            )
          );
          break;

        case 'agent_message':
          setIsStreaming(false);
          setCurrentToolCalls([]);
          break;

        case 'error':
          setMessages((prev) => [
            ...prev,
            {
              role: 'system',
              content: `Error: ${data.message}`,
              timestamp: new Date(),
            },
          ]);
          setIsStreaming(false);
          break;
      }
    };

    ws.onerror = () => {
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [agentName]);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current && isConnected) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'user',
          content,
          timestamp: new Date(),
        },
      ]);
      setIsStreaming(true);
      currentMessageRef.current = '';
      wsRef.current.send(
        JSON.stringify({
          type: 'user_message',
          content,
        })
      );
    }
  }, [isConnected]);

  return {
    messages,
    isConnected,
    isStreaming,
    currentToolCalls,
    sendMessage,
  };
}
