import { useEffect, useRef, useState, useCallback } from 'react';

export const useWebSocket = (projectId) => {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const isUnmountingRef = useRef(false);
  const seenMessagesRef = useRef(new Set());

  const connect = useCallback(() => {
    if (!projectId || isUnmountingRef.current) return;

    const wsUrl = `${window.location.origin.replace('http', 'ws')}/ws/projects/${projectId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Create a unique key for deduplication
        const msgKey = `${data.event}-${data.data?.page_id || data.data?.job_id || ''}-${data.data?.status || ''}`;
        
        // Skip if we've already seen this message (deduplication)
        if (seenMessagesRef.current.has(msgKey)) {
          return;
        }
        seenMessagesRef.current.add(msgKey);
        
        // Limit the seen set size to prevent memory leaks
        if (seenMessagesRef.current.size > 1000) {
          const arr = Array.from(seenMessagesRef.current);
          seenMessagesRef.current = new Set(arr.slice(-500));
        }
        
        setMessages((prev) => [...prev, data]);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Only reconnect if not unmounting
      if (!isUnmountingRef.current) {
        reconnectTimerRef.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [projectId]);

  useEffect(() => {
    connect();

    return () => {
      // Mark as unmounting to prevent reconnect
      isUnmountingRef.current = true;
      
      // Clear any pending reconnect timer
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      
      // Close the WebSocket connection
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    seenMessagesRef.current.clear();
  }, []);

  return { messages, isConnected, clearMessages };
};