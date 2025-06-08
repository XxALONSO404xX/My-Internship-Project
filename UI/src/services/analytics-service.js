/**
 * Stub analytics service.
 * Real implementation will integrate later.
 */
export function trackEvent(event, data = {}) {
  /* eslint-disable no-console */
  console.log(`[Analytics] ${event}`, data);
}
