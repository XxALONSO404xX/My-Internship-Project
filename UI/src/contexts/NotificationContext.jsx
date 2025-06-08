import React, { createContext, useState, useEffect } from 'react';
import { useToast } from '@chakra-ui/react';
import { API_BASE_URL } from '../services/auth-service.js';

// Create context
export const NotificationContext = createContext();

// Helper to determine backend WS endpoint
function getWebSocketUrl() {
  const url = new URL(API_BASE_URL);
  const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProtocol}//${url.host}/api/v1/ws/notifications`;
}

// Singleton WebSocket instance
let sharedSocket = null;
function getSharedSocket() {
  if (!sharedSocket || sharedSocket.readyState > WebSocket.OPEN) {
    const wsUrl = `${getWebSocketUrl()}?client_id=${crypto.randomUUID()}`;
    sharedSocket = new WebSocket(wsUrl);
  }
  return sharedSocket;
}

export function NotificationProvider({ children }) {
  const toast = useToast();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = getSharedSocket();

    // Set initial connected state without logging
    if (ws.readyState === WebSocket.OPEN) {
      setConnected(true);
    }

    const handleOpen = () => {
      setConnected(true);
      console.log('[WS] Connected to notification server');
    };
    const handleMessage = (event) => {
      console.log('[WS] raw message:', event.data);
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'notification' && msg.data) {
          const data = msg.data;
          // throttle rule execution to only completed events
          if (data.event_type === 'rule_execution') {
            if (data.status !== 'completed') return;
            const title = `Rule Execution ${data.status.charAt(0).toUpperCase() + data.status.slice(1)}`;
            const content = `Processed ${data.data.devices_processed} devices, applied ${data.data.rules_applied_count} rules.`;
            toast({ title, description: content, status: 'info', duration: 4000, isClosable: true, position: 'top-right' });
            return;
          }
          // other notifications
          const { title = 'Notification', content = '' } = data;
          toast({ title, description: content, status: 'info', duration: 4000, isClosable: true, position: 'top-right' });
        }
      } catch (err) {
        console.error('[WS] Error parsing message', err);
      }
    };
    const handleError = (err) => {
      console.warn('[WS] WebSocket error, closing', err);
      ws.close();
    };
    const handleClose = () => {
      setConnected(false);
      console.warn('[WS] Disconnected, will reconnect');
      // Reset socket to trigger reconnect on next call
      sharedSocket = null;
    };

    ws.addEventListener('open', handleOpen);
    ws.addEventListener('message', handleMessage);
    ws.addEventListener('error', handleError);
    ws.addEventListener('close', handleClose);

    return () => {
      ws.removeEventListener('open', handleOpen);
      ws.removeEventListener('message', handleMessage);
      ws.removeEventListener('error', handleError);
      ws.removeEventListener('close', handleClose);
    };
  }, []);

  return (
    <NotificationContext.Provider value={{ socket: sharedSocket, connected }}>
      {children}
    </NotificationContext.Provider>
  );
}
