import { apiRequest } from './api';

// Fetch recent activities
export async function fetchActivities({ skip = 0, limit = 100 } = {}) {
  const params = new URLSearchParams({ skip, limit });
  return apiRequest(`/api/v1/activities?${params.toString()}`, { method: 'GET' });
}

// Search activities via backend filters (not yet used in UI)
export async function searchActivities(filter = {}) {
  return apiRequest('/api/v1/activities/search', {
    method: 'POST',
    body: filter,
  });
}

// Fetch activity summary
export async function getActivitySummary(hours = 24) {
  return apiRequest(`/api/v1/activities/summary?hours=${hours}`, {
    method: 'GET'
  });
}

// Fetch activities in a date range for trending
export async function getActivitiesInRange(start_time, end_time, limit = 1000) {
  return apiRequest('/api/v1/activities/search', {
    method: 'POST',
    body: { start_time, end_time, limit }
  });
}
