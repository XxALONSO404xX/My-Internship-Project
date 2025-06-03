/**
 * Analytics Service
 * Tracks user events and interactions for analytics and monitoring
 */

const LOG_EVENTS = true; // Enable/disable console logging of events

/**
 * Track an event with optional metadata
 * @param {string} eventName - Name of the event to track
 * @param {Object} eventData - Additional data to associate with the event
 */
export function trackEvent(eventName, eventData = {}) {
  // Log event to console in development
  if (LOG_EVENTS) {
    console.log(`Analytics Event: ${eventName}`, eventData);
  }

  // Determine if we're in Electron or browser environment
  const isElectron = window.electron || window.electronAPI;
  const environment = isElectron ? 'electron' : 'browser';
  
  // Add standard properties to all events
  const enhancedData = {
    ...eventData,
    timestamp: new Date().toISOString(),
    environment,
    sessionId: getSessionId(),
  };

  try {
    // In production, send to actual analytics service
    if (process.env.NODE_ENV === 'production') {
      // If using Electron, send through IPC
      if (isElectron && window.electronAPI?.trackAnalytics) {
        window.electronAPI.trackAnalytics({
          event: eventName,
          data: enhancedData
        });
      } else {
        // In browser, could send to an analytics endpoint
        // This is a placeholder for actual implementation
        sendToAnalyticsServer(eventName, enhancedData);
      }
    }
    
    // Store event in local storage for debugging/history
    storeEventLocally(eventName, enhancedData);
    
    return true;
  } catch (error) {
    console.error('Analytics Error:', error);
    return false;
  }
}

/**
 * Get or create a unique session ID
 * @returns {string} Session ID
 */
function getSessionId() {
  let sessionId = sessionStorage.getItem('analytics_session_id');
  
  if (!sessionId) {
    sessionId = generateUniqueId();
    sessionStorage.setItem('analytics_session_id', sessionId);
  }
  
  return sessionId;
}

/**
 * Generate a unique ID for analytics
 * @returns {string} Unique ID
 */
function generateUniqueId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

/**
 * Store event in local storage for history/debugging
 * @param {string} eventName - Event name
 * @param {Object} eventData - Event data
 */
function storeEventLocally(eventName, eventData) {
  try {
    // Get existing events from localStorage
    const existingEvents = JSON.parse(localStorage.getItem('analytics_events') || '[]');
    
    // Add new event (limit to last 100 events to prevent localStorage overflow)
    const updatedEvents = [
      { name: eventName, data: eventData, time: new Date().toISOString() },
      ...existingEvents
    ].slice(0, 100);
    
    // Store back to localStorage
    localStorage.setItem('analytics_events', JSON.stringify(updatedEvents));
  } catch (error) {
    console.warn('Could not store analytics event locally:', error);
  }
}

/**
 * Send event to analytics server (placeholder)
 * @param {string} eventName - Event name
 * @param {Object} eventData - Event data
 */
function sendToAnalyticsServer(eventName, eventData) {
  // Placeholder for actual implementation
  // This would normally send a request to your analytics service
  console.log('Would send to analytics server:', eventName, eventData);
  
  // Example implementation using fetch:
  /*
  fetch('/api/analytics', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      event: eventName,
      data: eventData
    })
  }).catch(error => console.error('Analytics API error:', error));
  */
}

/**
 * Track page view
 * @param {string} pageName - Name of the page being viewed
 * @param {Object} additionalData - Additional data to track
 */
export function trackPageView(pageName, additionalData = {}) {
  trackEvent('page_view', {
    page: pageName,
    url: window.location.href,
    referrer: document.referrer,
    ...additionalData
  });
}

/**
 * Track authentication events
 * @param {string} action - Authentication action (login, register, etc.)
 * @param {string} status - Status of the action (success, failure)
 * @param {Object} additionalData - Additional data
 */
export function trackAuthEvent(action, status, additionalData = {}) {
  trackEvent(`auth_${action}_${status}`, additionalData);
}

/**
 * Get analytics history from local storage
 * @returns {Array} Array of tracked events
 */
export function getAnalyticsHistory() {
  try {
    return JSON.parse(localStorage.getItem('analytics_events') || '[]');
  } catch (error) {
    console.error('Error retrieving analytics history:', error);
    return [];
  }
}

/**
 * Clear analytics history from local storage
 */
export function clearAnalyticsHistory() {
  localStorage.removeItem('analytics_events');
}
