import React, { createContext, useState, useEffect, useRef } from 'react';
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

// Helper to defer toast calls out of the synchronous WS message handler
function scheduleToast(fn) {
  if (window.requestIdleCallback) {
    window.requestIdleCallback(fn);
  } else {
    setTimeout(fn, 0);
  }
}

// Queue WS messages for batched processing to minimize handler work
globalThis.messageQueue = globalThis.messageQueue || [];
let processingScheduled = false;

// Track processed executions to avoid duplicate toasts
globalThis.processedRuleExecSet = globalThis.processedRuleExecSet || new Set();

function processQueue() {
  processingScheduled = false;
  const queue = globalThis.messageQueue.splice(0);
  queue.forEach((text) => {
    // Only process relevant notification types
    if (!text.includes('"type":"notification"') && !text.includes('"type":"ruleCreated"') && !text.includes('"type":"ruleExecuted"')) {
      return;
    }
    let msg;
    try {
      msg = JSON.parse(text);
    } catch (err) {
      console.error('[WS] Error parsing message', err);
      return;
    }
    // Ignore rule-enabled notifications
    if (msg.type === 'notification' && msg.data) {
      const et = msg.data.event_type;
      // ignore rule_enabled & system notification_created spam
      if (et === 'rule_enabled' || et === 'notification_created') return;
    }
    // Handle rule execution notifications with dedupe
    if (msg.type === 'notification' && msg.data && msg.data.event_type === 'rule_execution') {
      // Only show rule execution notifications on the Rules page
      if (!window.location.pathname.includes('/rules')) return;
      const executionId = msg.data.execution_id || msg.data.id;
      if (globalThis.processedRuleExecSet.has(executionId)) return;
      globalThis.processedRuleExecSet.add(executionId);
      const ruleName = msg.data.ruleName || msg.data.rule_name || msg.data.name || 'Unnamed rule';
      const result = msg.data.result || msg.data.outcome || '';
      scheduleToast(() => {
        globalThis.toast({
          title: `Rule executed: ${ruleName}`,
          description: result ? `Result: ${result}` : undefined,
          status: 'info',
          duration: 4000,
          isClosable: true,
          position: 'top-right',
        });
      });
      return;
    }
    // Handle rule creation notifications
    if (msg.type === 'ruleCreated' && msg.data) {
      scheduleToast(() =>
        globalThis.toast({
          title: `Rule created: ${msg.data.name}`,
          status: 'success',
          duration: 3000,
          isClosable: true,
          position: 'top-right',
        })
      );
      return;
    }
    // Handle rule execution notifications
    if (msg.type === 'ruleExecuted' && msg.data) {
      const executionId = msg.data.id;
      if (globalThis.processedRuleExecSet.has(executionId)) return;
      globalThis.processedRuleExecSet.add(executionId);
      const ruleName = msg.data.ruleName || msg.data.rule_name || msg.data.name || 'Unnamed rule';
      const result = msg.data.result || msg.data.outcome || '';
      scheduleToast(() => {
        globalThis.toast({
          title: `Rule executed: ${ruleName}`,
          description: result ? `Result: ${result}` : undefined,
          status: 'info',
          duration: 4000,
          isClosable: true,
          position: 'top-right',
        });
      });
      return;
    }
    // General notifications
    if (msg.type === 'notification' && msg.data) {
      scheduleToast(() =>
        globalThis.toast({
          title: msg.data.title || 'Notification',
          description: msg.data.content || '',
          status: 'info',
          duration: 4000,
          isClosable: true,
          position: 'top-right',
        })
      );
    }
  });
}

function scheduleProcessing() {
  if (processingScheduled) return;
  processingScheduled = true;
  if (window.requestIdleCallback) {
    window.requestIdleCallback(processQueue, { timeout: 500 });
  } else {
    setTimeout(processQueue, 500);
  }
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
  // Expose toast globally for deferred processing
  globalThis.toast = toast;
  const [connected, setConnected] = useState(false);
  const processedRuleExec = useRef(new Set());

  useEffect(() => {
    const ws = getSharedSocket();

    // Set initial connected state without logging
    if (ws.readyState === WebSocket.OPEN) {
      setConnected(true);
    }

    const handleOpen = () => {
      // Clear any queued messages on reconnect to prevent spam
      globalThis.messageQueue = [];
      setConnected(true);
    };
    const handleMessage = (event) => {
      // Enqueue raw message and defer processing
      globalThis.messageQueue.push(event.data);
      scheduleProcessing();
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
