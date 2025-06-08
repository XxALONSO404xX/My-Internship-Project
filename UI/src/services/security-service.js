import { apiRequest } from './api';

// Start a vulnerability scan for a specific device
export async function startVulnerabilityScan(deviceId) {
  return apiRequest(`/api/v1/security/vulnerability/${deviceId}/scan`, {
    method: 'POST',
    body: {}
  });
}

// Get results of a vulnerability scan
export async function getVulnerabilityScanResults(scanId) {
  return apiRequest(`/api/v1/security/vulnerability/scan/${scanId}`, {
    method: 'GET'
  });
}

// Get vulnerability scan history for a specific device
export async function getDeviceVulnerabilityHistory(deviceId) {
  return apiRequest(`/api/v1/devices/${deviceId}/vulnerabilities`, {
    method: 'GET'
  });
}

// Remediate a single vulnerability by id
export async function remediateVulnerability(deviceId, vulnerabilityId) {
  return apiRequest(`/api/v1/security/remediation/vulnerability/${deviceId}/${vulnerabilityId}`, {
    method: 'POST',
    body: {}
  });
}

// Perform bulk remediation of vulnerabilities
export async function bulkRemediateVulnerabilities(remediationMap) {
  return apiRequest('/api/v1/security/remediation/bulk', {
    method: 'POST',
    body: remediationMap
  });
}

// Inject a simulated vulnerability into a device
export async function injectVulnerability(deviceId, vulnerability) {
  return apiRequest(`/api/v1/security/vulnerability/inject/${deviceId}`, {
    method: 'POST',
    body: vulnerability
  });
}
