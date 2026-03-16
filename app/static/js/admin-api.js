/**
 * AdminAPI — centralized fetch wrapper for LFA Admin UI.
 *
 * Every mutation in the admin panel goes through this client so that:
 *  - CSRF tokens are always included
 *  - Errors are normalized to a consistent shape
 *  - Toast notifications are shown automatically on success/error
 *
 * Usage:
 *   AdminAPI.post('/api/v1/tournaments/1/start', {})
 *     .then(data => toast('Tournament started'))
 *     .catch(err => toast(err.message, 'error'));
 */

class AdminAPIError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
    this.name = 'AdminAPIError';
  }
}

const AdminAPI = {
  /** Read the CSRF token from the cookie set by the backend. */
  csrfToken() {
    var m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  },

  /**
   * Core fetch wrapper.
   * @param {string} method  HTTP method (GET, POST, PATCH, DELETE, …)
   * @param {string} url     Absolute or root-relative URL
   * @param {object|null} body  JSON-serialisable request body (omit for GET)
   * @returns {Promise<any>}  Parsed JSON response body
   */
  async call(method, url, body = null) {
    const headers = {
      'Content-Type': 'application/json',
      'X-CSRF-Token': this.csrfToken(),
    };
    const opts = { method, headers, credentials: 'include' };
    if (body !== null) opts.body = JSON.stringify(body);

    let resp;
    try {
      resp = await fetch(url, opts);
    } catch (networkErr) {
      throw new AdminAPIError('Network error — check your connection', 0);
    }

    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const payload = await resp.json();
        msg = payload?.error?.message ?? payload?.detail ?? msg;
      } catch (_) { /* non-JSON error body */ }
      throw new AdminAPIError(msg, resp.status);
    }

    // 204 No Content
    if (resp.status === 204) return null;
    return resp.json();
  },

  /** Convenience wrappers */
  get(url)            { return this.call('GET',    url, null); },
  post(url, body)     { return this.call('POST',   url, body ?? {}); },
  patch(url, body)    { return this.call('PATCH',  url, body ?? {}); },
  put(url, body)      { return this.call('PUT',    url, body ?? {}); },
  delete(url)         { return this.call('DELETE', url, null); },
};

/**
 * toast(message, type)
 *
 * Display a self-dismissing notification at the bottom-right of the screen.
 * Types: 'success' (default) | 'error' | 'warning' | 'info'
 *
 * Requires #toast-container in the DOM (added by admin_base.html).
 */
function toast(msg, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) { console.warn('[toast] #toast-container not found'); return; }

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  container.appendChild(el);

  // Remove after animation completes (4 s = 3.7 s delay + 0.3 s fade)
  setTimeout(() => { el.remove(); }, 4000);
}
