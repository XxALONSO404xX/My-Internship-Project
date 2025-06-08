import { getAuthHeaders, API_BASE_URL } from './auth-service';

/**
 * Generic helper to perform authenticated API requests.
 * Automatically prefixes the path with API_BASE_URL and injects the Bearer token.
 * Returns parsed JSON or throws with a helpful message.
 *
 * @param {string} path e.g. "/api/v1/devices"
 * @param {Object} options fetch options (method, headers, body)
 */
export async function apiRequest(path, options = {}) {
  const authHeaders = await getAuthHeaders();
  const headers = {
    ...authHeaders,
    ...(options.headers || {})
  };

  const opts = { ...options, headers };

  if (opts.body && typeof opts.body !== 'string') {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }

  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, opts);

  let data = {};
  try {
    data = await res.json();
  } catch (_) {
    // Non-JSON response; ignore.
  }

  if (!res.ok) {
    const msg = data.detail || data.error || `${res.status} ${res.statusText}`;
    throw new Error(msg);
  }
  return data;
}
