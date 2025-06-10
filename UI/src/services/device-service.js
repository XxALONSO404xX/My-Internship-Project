import axios from 'axios';
import { getAuthHeaders, API_BASE_URL } from './auth-service';

/**
 * Fetch list of devices from backend
 * @returns {Promise<Array>} Array of device objects
 */
export async function getDevices() {
  try {
    const headers = await getAuthHeaders();
    const res = await axios.get(`${API_BASE_URL}/api/v1/devices`, { headers });
    return res.data;
  } catch (err) {
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message;
    console.error('Error fetching devices:', err);
    throw new Error(msg);
  }
}

/**
 * Fetch a single device by ID
 * @param {string} id
 * @returns {Promise<Object>}
 */
export async function getDevice(id) {
  try {
    const headers = await getAuthHeaders();
    const res = await axios.get(`${API_BASE_URL}/api/v1/devices/${id}`, { headers });
    return res.data;
  } catch (err) {
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message;
    console.error(`Error fetching device ${id}:`, err);
    throw new Error(msg);
  }
}

/**
 * Toggle power state of a device
 * @param {string} id
 * @param {boolean} turnOn
 * @returns {Promise<Object>}
 */
export async function toggleDevicePower(id, turnOn) {
  try {
    const headers = await getAuthHeaders();
    const action = turnOn ? 'turn_on' : 'turn_off';
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/devices/${id}/control?action=${action}`,
      {},
      { headers }
    );
    return res.data;
  } catch (err) {
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message;
    console.error(`Error toggling power for device ${id}:`, err);
    throw new Error(msg);
  }
}

/**
 * Start vulnerability scan for a device
 * @param {string} id
 * @returns {Promise<Object>} scan result
 */
export const scanDevice = async (deviceId) => {
  if (!deviceId) throw new Error('Device ID is required for scanning');
  try {
    const headers = await getAuthHeaders();
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/security/vulnerability/${deviceId}/scan`, {}, { headers }
    );
    return res.data;
  } catch (err) {
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message;
    console.error(`Error scanning device ${deviceId}:`, err);
    throw new Error(msg);
  }
};

/**
 * Fetch latest sensor readings for a device
 * @param {string} id
 * @returns {Promise<Object>} readings mapping
 */
export async function getLatestReadings(id) {
  try {
    const headers = await getAuthHeaders();
    const res = await axios.get(`${API_BASE_URL}/api/v1/devices/${id}/sensors/latest`, { headers });
    return res.data.readings;
  } catch (err) {
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message;
    console.error(`Error fetching latest readings for device ${id}:`, err);
    throw new Error(msg);
  }
}

/**
 * Simulate sensor metrics generation for a specific device (for demo/testing)
 * @param {string} id
 * @param {Object} metrics optional override readings
 */
export async function simulateDeviceMetrics(id, metrics = {}) {
  try {
    const headers = await getAuthHeaders();
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/devices/${id}/simulate/metrics`,
      { device_id: id, ...metrics },
      { headers }
    );
    return res.data;
  } catch (err) {
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message;
    console.error(`Error simulating metrics for device ${id}:`, err);
    throw new Error(msg);
  }
}

/**
 * Fetch vulnerabilities for a device
 * @param {string} id
 * @returns {Promise<Object>} vulnerability response
 */
export async function getDeviceVulnerabilities(id) {
  try {
    const headers = await getAuthHeaders();
    const res = await axios.get(`${API_BASE_URL}/api/v1/devices/${id}/vulnerabilities`, { headers });
    return res.data;
  } catch (err) {
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message;
    console.error(`Error fetching vulnerabilities for device ${id}:`, err);
    throw new Error(msg);
  }
}

/**
 * Fetch vulnerability scan results for a given scan ID
 * @param {string} scanId
 * @returns {Promise<Object>} scan results
 */
export async function getVulnerabilityScanResults(scanId) {
  try {
    const headers = await getAuthHeaders();
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/security/vulnerability/scan/${scanId}`,
      { headers }
    );
    return res.data;
  } catch (err) {
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message;
    console.error(`Error fetching scan results for scan ${scanId}:`, err);
    throw new Error(msg);
  }
}
