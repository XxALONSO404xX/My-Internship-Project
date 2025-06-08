import { getAuthHeaders, API_BASE_URL } from './auth-service';

/**
 * Fetch sensor readings for a device
 * @param {string} deviceId
 * @param {object} options { sensorType, limit, offset, startTime, endTime }
 * @returns {Promise<Array>} readings array
 */
export async function getDeviceReadings(deviceId, options = {}) {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams();
  if (options.sensorType) params.append('sensor_type', options.sensorType);
  if (options.limit) params.append('limit', options.limit);
  if (options.offset) params.append('offset', options.offset);
  if (options.startTime) params.append('start_time', options.startTime);
  if (options.endTime) params.append('end_time', options.endTime);
  const query = params.toString() ? `?${params.toString()}` : '';
  const resp = await fetch(`${API_BASE_URL}/api/v1/devices/${deviceId}/readings${query}`, {
    method: 'GET',
    headers
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || data.error || resp.statusText);
  }
  return resp.json();
}

/**
 * Get summary of all sensors in the system
 * @returns {Promise<Object>} summary object
 */
export async function getSensorsSummary() {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/api/v1/devices/sensors/summary`, {
    method: 'GET',
    headers
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || data.error || resp.statusText);
  }
  return resp.json();
}
