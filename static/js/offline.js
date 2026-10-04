/* ── IndexedDB Setup ───────────────────────────────────────────────────── */
const DB = {
  db: null,
  dbName: 'pfams_offline',
  version: 1,

  currentUserId() {
    return document.body.dataset.userId || '';
  },

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
    const userId = this.currentUserId();
    if (!userId) throw new Error('Sign in before saving offline transactions.');
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('pending_ops', 'readwrite');
      operation.client_id = operation.client_id || 'op_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      operation.queued_at = new Date().toISOString();
      operation.user_id = userId;
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
      req.onsuccess = () => resolve(
        req.result
          .filter(operation => operation.user_id === this.currentUserId())
          .sort((left, right) => left.queued_at.localeCompare(right.queued_at))
      );
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

      const body = new FormData();
      body.append('operations', JSON.stringify(pending.map(operation => {
        const payload = { ...operation };
        delete payload.user_id;
        delete payload.queued_at;
        delete payload.file;
        if (operation.file?.blob) {
          const fileKey = `upload_${operation.client_id}`;
          payload.file_key = fileKey;
          payload.file_field = operation.file.field;
          body.append(
            fileKey,
            new File([operation.file.blob], operation.file.name, {
              type: operation.file.type,
            })
          );
        }
        return payload;
      })));

      const res = await fetch('/api/sync/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
        },
        body,
      });

      if (!res.ok) throw new Error('Sync failed: ' + res.status);

      const data = await res.json();
      for (const result of (data.results || [])) {
        if (result.status === 'ok') {
          await DB.removePending(result.client_id);
        }
      }
      const failed = (data.results || []).filter(
        result => result.status !== 'ok'
      ).length;

      const remaining = await DB.getPending();
      this.updateUI(remaining.length);
      if (data.synced > 0) {
        if (typeof Toast !== 'undefined') Toast.show(`Synced ${data.synced} offline transaction(s).`, 'success');
      }
      if (failed > 0 && typeof Toast !== 'undefined') {
        Toast.show(
          `${failed} queued transaction(s) could not sync and remain saved on this device.`,
          'warning'
        );
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
    if ('serviceWorker' in navigator && 'sync' in ServiceWorkerRegistration.prototype) {
      navigator.serviceWorker.ready
        .then(registration => registration.sync.register('sync-transactions'))
        .catch(() => {});
    }
    return clientId;
  }
};

async function queueOfflineForm(event) {
  const form = event.currentTarget;
  if (navigator.onLine) return;
  event.preventDefault();

  if (!form.reportValidity()) return;

  const data = {};
  let queuedFile = null;
  for (const [key, value] of new FormData(form).entries()) {
    if (value instanceof File && value.size > 0) {
      const allowedTypes = form.dataset.offlineType === 'profile'
        ? ['image/jpeg', 'image/png', 'image/gif']
        : ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
      if (value.size > 5242880 || !allowedTypes.includes(value.type)) {
        Toast.show('Choose an allowed file smaller than 5 MB.', 'warning');
        return;
      }
      queuedFile = {
        blob: value,
        name: value.name,
        type: value.type,
        field: {
          income: 'attachment',
          expense: 'receipt',
          profile: 'profile_photo',
        }[form.dataset.offlineType],
      };
    } else if (!(value instanceof File) && key !== 'csrfmiddlewaretoken') {
      data[key] = value;
    }
  }
  if (
    ['income', 'expense'].includes(form.dataset.offlineType) &&
    (!data.amount || Number(data.amount) <= 0)
  ) {
    Toast.show('Enter an amount greater than zero.', 'warning');
    return;
  }

  try {
    await SyncManager.queueOperation({
      type: form.dataset.offlineType,
      action: form.dataset.offlineType === 'profile' ? 'update' : 'create',
      data,
      file: queuedFile,
    });
    if (form.dataset.offlineType !== 'profile') {
      form.reset();
      const dateInput = form.querySelector('input[name="date"]');
      if (dateInput) dateInput.value = new Date().toISOString().slice(0, 10);
    }
    let notice = form.querySelector('[data-offline-queued]');
    if (!notice) {
      notice = document.createElement('div');
      notice.dataset.offlineQueued = 'true';
      notice.className = 'alert alert-info';
      notice.setAttribute('role', 'status');
      form.prepend(notice);
    }
    notice.textContent = 'Saved on this device. It will sync when you are back online.';
  } catch (error) {
    Toast.show(error.message || 'Could not save this transaction offline.', 'danger');
  }
}

/* ── Init */
document.addEventListener('DOMContentLoaded', async () => {
  ConnectionManager.init();
  const pending = await DB.getPending().catch(() => []);
  SyncManager.updateUI(pending.length);

  // Manual sync button
  document.getElementById('manual-sync-btn')?.addEventListener('click', () => SyncManager.syncNow());
  document.querySelectorAll('form[data-offline-type]').forEach((form) => {
    form.addEventListener('submit', queueOfflineForm);
  });
  navigator.serviceWorker?.addEventListener('message', (event) => {
    if (event.data?.type === 'SYNC_NOW') SyncManager.syncNow();
  });

  // If online and has pending, sync immediately
  if (ConnectionManager.isOnline && pending.length > 0) {
    SyncManager.syncNow();
  }
});
