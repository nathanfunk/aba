import { useEffect, useRef, useState, useCallback } from 'react';

export interface Message {
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  tools?: ToolCall[];
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
              const lastMsg = prev[prev.length - 1];
              if (lastMsg && lastMsg.role === 'agent') {
                // Create new message object (don't mutate)
                return [
                  ...prev.slice(0, -1),
                  {
                    ...lastMsg,
                    content: currentMessageRef.current,
                  },
                ];
              } else {
                return [
                  ...prev,
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
            // Don't clear currentMessageRef here - it will be cleared when next message starts
            // This prevents race condition where the final message might be lost
          }
          break;

        case 'tool_start':
          console.log(`[WebSocket] Tool starting: ${data.tool_name}`, data.arguments);
          // Finalize current text message if any, then add tool as separate message
          setMessages((prev) => {
            const lastMsg = prev[prev.length - 1];

            // If currently building an agent message, we'll add the tool to it
            // Otherwise create a new message for the tool
            if (lastMsg && lastMsg.role === 'agent') {
              const existingTools = lastMsg.tools || [];
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMsg,
                  tools: [
                    ...existingTools,
                    {
                      name: data.tool_name || 'unknown',
                      arguments: data.arguments || {},
                    },
                  ],
                },
              ];
            } else {
              // No agent message yet, create one just for the tool
              return [
                ...prev,
                {
                  role: 'agent',
                  content: '',
                  timestamp: new Date(),
                  tools: [
                    {
                      name: data.tool_name || 'unknown',
                      arguments: data.arguments || {},
                    },
                  ],
                },
              ];
            }
          });
          // Reset current message ref so next stream_chunk creates a new message
          currentMessageRef.current = '';
          break;

        case 'tool_result':
          console.log(`[WebSocket] Tool result: ${data.tool_name} (success=${data.success})`);
          // Find and update the tool result in the most recent message with this tool
          setMessages((prev) => {
            // Search backwards for the message containing this tool
            for (let i = prev.length - 1; i >= 0; i--) {
              const msg = prev[i];
              if (msg.tools && msg.tools.some(t => t.name === data.tool_name && !t.result)) {
                return [
                  ...prev.slice(0, i),
                  {
                    ...msg,
                    tools: msg.tools.map((tool) =>
                      tool.name === data.tool_name && !tool.result
                        ? { ...tool, result: data.result, success: data.success }
                        : tool
                    ),
                  },
                  ...prev.slice(i + 1),
                ];
              }
            }
            return prev;
          });
          break;

        case 'agent_message':
          console.log('[WebSocket] Agent message complete');
          setIsStreaming(false);
          // Tool calls are already attached via tool_start/tool_result
          // No need to do anything here
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

  const clearMessages = useCallback(() => {
    setMessages([]);
    currentMessageRef.current = '';
    setIsStreaming(false);
  }, []);

  return {
    messages,
    isConnected,
    isStreaming,
    sendMessage,
    clearMessages,
  };
}
