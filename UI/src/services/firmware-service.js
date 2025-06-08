import { apiRequest } from './api';

// List compatible firmware versions for a device
export async function getCompatibleFirmware(deviceId) {
  return apiRequest(`/api/v1/firmware/device/${deviceId}/compatible`, {
    method: 'GET'
  });
}

// Start firmware update for a device
export async function startFirmwareUpdate(deviceId, firmwareVersion, force = false) {
  return apiRequest('/api/v1/firmware/update', {
    method: 'POST',
    body: {
      device_id: deviceId,
      firmware_version: firmwareVersion,
      force_update: force
    }
  });
}

// Get firmware update status by update_id returned above
export async function getUpdateStatus(updateId) {
  return apiRequest(`/api/v1/firmware/update/${updateId}`, {
    method: 'GET'
  });
}

// Check device firmware status (optionally include vulnerabilities)
export async function checkDeviceFirmwareStatus(deviceId) {
  return apiRequest(`/api/v1/firmware/status/device/${deviceId}?include_vulnerabilities=true`, {
    method: 'GET'
  });
}
