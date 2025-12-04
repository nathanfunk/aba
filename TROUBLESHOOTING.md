# Troubleshooting the ABA Web Interface

This guide helps you troubleshoot issues with the ABA web interface.

## Viewing Logs

The web interface includes comprehensive logging on both the server and client sides.

### Server-Side Logs

Server logs are output to the terminal where you run `aba-web`. They show:
- WebSocket connection events
- Message processing
- Tool execution
- OpenRouter API interactions
- Errors and warnings

**Log format:**
```
2025-12-03 10:30:45 - aba.web.server - INFO - WebSocket connection accepted for agent 'agent-builder'
2025-12-03 10:30:47 - aba.web.agent_session - INFO - Handling user message (length=42)
2025-12-03 10:30:48 - aba.web.streaming_model - INFO - Starting chat stream with model=openai/gpt-4o-mini, tools=yes
```

**Key log locations to check:**
- `aba.web.server` - WebSocket connections and message routing
- `aba.web.agent_session` - Message handling, tool execution
- `aba.web.streaming_model` - OpenRouter API streaming

### Client-Side Logs

Client logs appear in your browser's developer console. They show:
- WebSocket connection status
- Messages sent and received
- Tool execution progress
- Connection errors

**To view client logs:**
1. Open your browser's Developer Tools (F12 or Ctrl+Shift+I)
2. Go to the "Console" tab
3. Look for messages prefixed with `[WebSocket]`

**Example client logs:**
```
[WebSocket] Connecting to ws://localhost:8000/ws/chat/agent-builder
[WebSocket] Connection opened
[WebSocket] Received message type: info
[WebSocket] Sending message (length=15)
[WebSocket] Stream complete
```

## Common Issues

### Issue: WebSocket Shows "Disconnected" After a Few Messages

**Symptoms:**
- Connection works initially
- After 2-3 messages, shows "Disconnected"
- Refreshing the page fixes it temporarily

**Diagnosis:**
1. Check server logs for disconnection reason:
   ```
   Client disconnected from agent 'agent-builder' (code=1000, reason=none)
   ```

2. Check client logs for close event:
   ```
   [WebSocket] Connection closed (code=1000, reason=none, clean=true)
   ```

**Common causes:**

**A. Timeout (60 seconds)**
- Server has a 60-second timeout for OpenRouter requests
- If response takes longer, connection times out
- **Log indicators:**
  ```
  OpenRouter request timed out after 60.0 seconds
  ```
- **Solution:** Long-running operations should complete within 60s, or timeout needs adjustment in `streaming_model.py:28`

**B. Network error or connection dropped**
- **Log indicators:**
  ```
  Remote protocol error (connection closed): ...
  Unexpected streaming error: ...
  ```
- **Solution:** Check network connection, firewall settings

**C. Uncaught exception**
- **Log indicators:**
  ```
  Unexpected error in handle_user_message: ...
  Session error: ...
  ```
- **Solution:** Check full traceback in server logs, report as bug

**D. OpenRouter API error**
- **Log indicators:**
  ```
  OpenRouter API error: status=429, body=...
  Error in streaming chunk: ...
  ```
- **Solution:** Check API key, rate limits, model availability

### Issue: No Response from Agent

**Symptoms:**
- Message sent but no response
- Connection still shows "Connected"
- No error message

**Diagnosis:**
1. Check server logs for message processing:
   ```
   Processing user message #1 (length=15)
   Starting chat stream with model=...
   ```

2. If you see "Starting chat stream" but nothing after:
   - OpenRouter may be slow
   - Check for timeout or API errors in logs

3. Check client logs:
   ```
   [WebSocket] Sending message (length=15)
   [WebSocket] Received message type: stream_chunk
   ```

### Issue: Tools Not Executing

**Symptoms:**
- Agent tries to use tools but they don't work
- Error messages about tools not found

**Diagnosis:**
1. Check agent capabilities in server logs:
   ```
   Loaded agent 'agent-builder' with 3 capabilities
   Session initialized with 12 tools
   ```

2. Check for tool execution errors:
   ```
   Tool 'read_file' not found in available tools
   Error executing tool: ...
   ```

3. Verify agent has required capabilities in `~/.aba/agents/{agent-name}.json`

## Enabling Debug Logging

For more detailed logs, you can enable DEBUG level logging:

**Edit `src/aba/web/server.py:244`:**
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

This will show additional details like:
- Individual tool call iterations
- Message building
- Tool result details

## Getting Help

If you're still experiencing issues:

1. **Collect logs:**
   - Copy server logs from terminal
   - Copy client logs from browser console
   - Note the exact steps to reproduce

2. **Report the issue:**
   - GitHub: https://github.com/nathanfunk/aba/issues
   - Include logs and reproduction steps

## Log Rotation

Server logs are output to stdout/stderr by default. For production use, consider:
- Redirecting to a file: `aba-web > server.log 2>&1`
- Using a process manager with log rotation (systemd, supervisor, pm2)
- Setting up proper log aggregation
