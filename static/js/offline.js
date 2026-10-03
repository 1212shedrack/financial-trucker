/* ── IndexedDB Setup ───────────────────────────────────────────────────── */
const DB = {
  db: null,
  dbName: 'pfams_offline',
  version: 1,

  async open() {
    if (this.db) return this.db;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(this.dbName, this.version);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('pending_ops')) {
          const store = db.createObjectStore('pending_ops', { keyPath: 'client_id' });
          store.createIndex('type', 'type', { unique: false });
        }
      };
      req.onsuccess = (e) => { this.db = e.target.result; resolve(this.db); };
      req.onerror = (e) => reject(e.target.error);
    });
  },

  async savePending(operation) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('pending_ops', 'readwrite');
      operation.client_id = operation.client_id || 'op_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      operation.queued_at = new Date().toISOString();
      tx.objectStore('pending_ops').put(operation);
      tx.oncomplete = () => resolve(operation.client_id);
      tx.onerror = (e) => reject(e.target.error);
    });
  },

  async getPending() {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('pending_ops', 'readonly');
      const req = tx.objectStore('pending_ops').getAll();
      req.onsuccess = () => resolve(req.result);
      req.onerror = (e) => reject(e.target.error);
    });
  },

  async removePending(clientId) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('pending_ops', 'readwrite');
      tx.objectStore('pending_ops').delete(clientId);
      tx.oncomplete = resolve;
      tx.onerror = (e) => reject(e.target.error);
    });
  },

  async clearAll() {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('pending_ops', 'readwrite');
      tx.objectStore('pending_ops').clear();
      tx.oncomplete = resolve;
      tx.onerror = (e) => reject(e.target.error);
    });
  }
};

/* ── Connection Manager ────────────────────────────────────────────────── */
const ConnectionManager = {
  isOnline: navigator.onLine,

  init() {
    window.addEventListener('online',  () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());
    this.updateUI();
  },

  handleOnline() {
    this.isOnline = true;
    this.updateUI();
    console.log('[PFAMS] Back online — starting sync...');
    SyncManager.syncNow();
    if (typeof Toast !== 'undefined') Toast.show('You are back online. Syncing data...', 'success');
  },

  handleOffline() {
    this.isOnline = false;
    this.updateUI();
    if (typeof Toast !== 'undefined') Toast.show('You are offline. Data will sync when reconnected.', 'warning');
  },

  updateUI() {
    const indicator = document.getElementById('connection-indicator');
    const mobileIndicator = document.getElementById('mobile-connection-indicator');
    const text      = document.getElementById('conn-text');
    const mobileText = document.getElementById('mobile-conn-text');
    if (!indicator && !mobileIndicator) return;
    if (this.isOnline) {
      if (indicator) indicator.className = 'badge me-2 bg-success topbar-status';
      if (mobileIndicator) mobileIndicator.dataset.status = 'online';
      if (text) text.textContent = 'Online';
      if (mobileText) mobileText.textContent = 'Online';
    } else {
      if (indicator) indicator.className = 'badge me-2 bg-danger topbar-status';
      if (mobileIndicator) mobileIndicator.dataset.status = 'offline';
      if (text) text.textContent = 'Offline';
      if (mobileText) mobileText.textContent = 'Offline';
    }
  }
};

/* ── Sync Manager ──────────────────────────────────────────────────────── */
const SyncManager = {
  _syncing: false,

  async syncNow() {
    if (this._syncing || !ConnectionManager.isOnline) return;
    this._syncing = true;
    try {
      const pending = await DB.getPending();
      if (pending.length === 0) { this.updateUI(0); return; }

      const csrfToken = document.cookie.split('; ')
        .find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';

      const res = await fetch('/api/sync/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ operations: pending })
      });

      if (!res.ok) throw new Error('Sync failed: ' + res.status);

      const data = await res.json();
      for (const result of (data.results || [])) {
        if (result.status === 'ok') {
          await DB.removePending(result.client_id);
        }
      }

      const remaining = await DB.getPending();
      this.updateUI(remaining.length);
      if (data.synced > 0) {
        if (typeof Toast !== 'undefined') Toast.show(`Synced ${data.synced} offline transaction(s).`, 'success');
      }
    } catch (err) {
      console.warn('[PFAMS] Sync error:', err);
    } finally {
      this._syncing = false;
    }
  },

  updateUI(count) {
    const badge = document.getElementById('sync-badge');
    const countEl = document.getElementById('sync-count');
    if (!badge) return;
    if (count > 0) {
      badge.classList.remove('d-none');
      if (countEl) countEl.textContent = count;
    } else {
      badge.classList.add('d-none');
    }
  },

  async queueOperation(operation) {
    const clientId = await DB.savePending(operation);
    const pending = await DB.getPending();
    this.updateUI(pending.length);
    if (typeof Toast !== 'undefined') Toast.show('Saved offline. Will sync when online.', 'info');
    return clientId;
  }
};

/* ── Init */
document.addEventListener('DOMContentLoaded', async () => {
  ConnectionManager.init();
  const pending = await DB.getPending().catch(() => []);
  SyncManager.updateUI(pending.length);

  // Manual sync button
  document.getElementById('manual-sync-btn')?.addEventListener('click', () => SyncManager.syncNow());

  // If online and has pending, sync immediately
  if (ConnectionManager.isOnline && pending.length > 0) {
    SyncManager.syncNow();
  }
});
