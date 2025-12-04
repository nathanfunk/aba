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
  const reconnectTimeoutRef = useRef<number | null>(null);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    const wsUrl = `ws://${window.location.hostname}:8000/ws/chat/${agentName}`;
    console.log(`[WebSocket] Connecting to ${wsUrl}`);

    // Clear any existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[WebSocket] Connection opened');
      setIsConnected(true);
      // Clear any pending reconnect attempts
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);
      console.log(`[WebSocket] Received message type: ${data.type}`);

      switch (data.type) {
        case 'info':
          console.log(`[WebSocket] Info: ${data.message}`);
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
            console.log('[WebSocket] Stream complete');
            setIsStreaming(false);
            currentMessageRef.current = '';
          }
          break;

        case 'tool_start':
          console.log(`[WebSocket] Tool starting: ${data.tool_name}`, data.arguments);
          setCurrentToolCalls((prev) => [
            ...prev,
            {
              name: data.tool_name || 'unknown',
              arguments: data.arguments || {},
            },
          ]);
          break;

        case 'tool_result':
          console.log(`[WebSocket] Tool result: ${data.tool_name} (success=${data.success})`);
          setCurrentToolCalls((prev) =>
            prev.map((tool) =>
              tool.name === data.tool_name
                ? { ...tool, result: data.result, success: data.success }
                : tool
            )
          );
          break;

        case 'agent_message':
          console.log('[WebSocket] Agent message complete');
          setIsStreaming(false);
          setCurrentToolCalls([]);
          break;

        case 'error':
          console.error(`[WebSocket] Error: ${data.message}`);
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

        default:
          console.warn(`[WebSocket] Unknown message type: ${data.type}`);
      }
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      setIsConnected(false);
      setIsStreaming(false); // Reset streaming state on error
    };

    ws.onclose = (event) => {
      console.log(`[WebSocket] Connection closed (code=${event.code}, reason=${event.reason || 'none'}, clean=${event.wasClean})`);
      setIsConnected(false);
      setIsStreaming(false); // Reset streaming state on close

      // Attempt to reconnect if we should and it wasn't a normal closure
      if (shouldReconnectRef.current && event.code !== 1000) {
        console.log('[WebSocket] Attempting to reconnect in 2 seconds...');
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, 2000);
      }
    };

    wsRef.current = ws;
  }, [agentName]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    // Handle page visibility changes (iOS app suspend/resume)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('[WebSocket] Page became visible, checking connection...');
        // Check if connection is broken
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
          console.log('[WebSocket] Connection lost, reconnecting...');
          setIsStreaming(false); // Reset streaming state
          connect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      shouldReconnectRef.current = false;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current && isConnected) {
      console.log(`[WebSocket] Sending message (length=${content.length})`);
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
    } else {
      console.warn(`[WebSocket] Cannot send message - connected=${isConnected}, ws=${wsRef.current ? 'exists' : 'null'}`);
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
