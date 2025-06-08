import { apiRequest } from './api';

// Get all rules
export async function listRules() {
  return apiRequest('/api/v1/rules', { method: 'GET' });
}

// Create a rule (ruleData should match RuleCreate schema)
export async function createRule(ruleData) {
  return apiRequest('/api/v1/rules', {
    method: 'POST',
    body: ruleData,
  });
}

// Update a rule
export async function updateRule(ruleId, ruleData) {
  return apiRequest(`/api/v1/rules/${ruleId}`, {
    method: 'PUT',
    body: ruleData,
  });
}

// Delete a rule
export async function deleteRule(ruleId) {
  return apiRequest(`/api/v1/rules/${ruleId}`, {
    method: 'DELETE',
  });
}

// Enable a rule
export async function enableRule(ruleId) {
  return apiRequest(`/api/v1/rules/${ruleId}/enable`, {
    method: 'POST',
  });
}

// Disable a rule
export async function disableRule(ruleId) {
  return apiRequest(`/api/v1/rules/${ruleId}/disable`, {
    method: 'POST',
  });
}

// Apply all rules (force evaluation)
export async function applyAllRules() {
  return apiRequest('/api/v1/rules/apply', { method: 'POST' });
}

// Apply rules to a specific device
export async function applyRulesToDevice(deviceId) {
  return apiRequest(`/api/v1/rules/device/${deviceId}/apply`, {
    method: 'POST',
  });
}

// Get active rule executions
export async function getActiveExecutions() {
  return apiRequest('/api/v1/rules/executions', { method: 'GET' });
}

// Cancel all executions
export async function cancelAllExecutions() {
  return apiRequest('/api/v1/rules/cancel', { method: 'POST' });
}

// Cancel a specific execution by ID
export async function cancelExecution(executionId) {
  return apiRequest(`/api/v1/rules/cancel/${executionId}`, { method: 'POST' });
}
