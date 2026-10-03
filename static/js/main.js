/* ── Theme Manager ─────────────────────────────────────────────────────── */
const ThemeManager = {
  init() {
    const saved = localStorage.getItem('pfams_theme') || 'light';
    this.apply(saved);
  },
  apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.querySelectorAll('#themeIcon, .theme-icon').forEach((icon) => {
      icon.className = theme === 'dark' ? 'bi bi-sun theme-icon' : 'bi bi-moon theme-icon';
    });
    localStorage.setItem('pfams_theme', theme);
    document.dispatchEvent(new CustomEvent('pfams:themechange', { detail: { theme } }));
  },
  colors() {
    const styles = getComputedStyle(document.documentElement);
    return {
      text: styles.getPropertyValue('--color-text-primary').trim(),
      muted: styles.getPropertyValue('--color-text-muted').trim(),
      border: styles.getPropertyValue('--color-border').trim(),
      grid: styles.getPropertyValue('--color-divider').trim(),
      surface: styles.getPropertyValue('--color-card').trim(),
    };
  },
  toggle() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    this.apply(current === 'dark' ? 'light' : 'dark');
  }
};
window.ThemeManager = ThemeManager;

/* ── Sidebar Manager ───────────────────────────────────────────────────── */
const SidebarManager = {
  sidebar: null,
  overlay: null,

  init() {
    this.sidebar = document.getElementById('sidebar');
    this.overlay = document.getElementById('sidebarOverlay');
    const toggleBtn  = document.getElementById('sidebarToggle');
    const closeBtn   = document.getElementById('sidebarClose');

    if (toggleBtn) toggleBtn.addEventListener('click', () => this.toggle());
    if (closeBtn)  closeBtn.addEventListener('click',  () => this.close());
    if (this.overlay) this.overlay.addEventListener('click', () => this.close());
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') this.close();
    });
    window.addEventListener('resize', () => {
      if (window.matchMedia('(min-width: 992px)').matches) this.close();
    });
  },

  toggle() {
    if (this.sidebar.classList.contains('show')) {
      this.close();
    } else {
      this.open();
    }
  },

  open() {
    this.sidebar?.classList.add('show');
    this.overlay?.classList.add('show');
    document.getElementById('sidebarToggle')?.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  },

  close() {
    this.sidebar?.classList.remove('show');
    this.overlay?.classList.remove('show');
    document.getElementById('sidebarToggle')?.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }
};

/* GET filters submit immediately for discrete controls and debounce text search. */
const AutoFilterManager = {
  init() {
    document.querySelectorAll('form.auto-filter-form').forEach((form) => {
      let searchTimer;
      form.querySelectorAll('select, input[type="date"], input[type="number"]').forEach((control) => {
        control.addEventListener('change', () => form.requestSubmit());
      });
      form.querySelectorAll('input[type="search"], input[name="q"]').forEach((control) => {
        control.addEventListener('input', () => {
          window.clearTimeout(searchTimer);
          searchTimer = window.setTimeout(() => form.requestSubmit(), 350);
        });
      });
    });
  }
};
window.AutoFilterManager = AutoFilterManager;

/* ── Currency Formatter ────────────────────────────────────────────────── */
const CurrencyFormatter = {
  format(amount, symbol = 'TSh') {
    const num = parseFloat(amount) || 0;
    return symbol + ' ' + num.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  },
  parse(str) {
    return parseFloat(str.replace(/[^0-9.-]/g, '')) || 0;
  }
};

/* ── Toast Notifications ───────────────────────────────────────────────── */
const Toast = {
  show(message, type = 'success') {
    const container = document.getElementById('toast-container') || this._createContainer();
    const id = 'toast-' + Date.now();
    const icons = { success: 'bi-check-circle', danger: 'bi-x-circle', warning: 'bi-exclamation-triangle', info: 'bi-info-circle' };
    const html = `
      <div id="${id}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive">
        <div class="d-flex">
          <div class="toast-body"><i class="bi ${icons[type] || icons.info} me-2"></i>${message}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>`;
    container.insertAdjacentHTML('beforeend', html);
    const el = document.getElementById(id);
    const toast = new bootstrap.Toast(el, { delay: 4000 });
    toast.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
  },
  _createContainer() {
    const div = document.createElement('div');
    div.id = 'toast-container';
    div.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    div.style.zIndex = '9999';
    document.body.appendChild(div);
    return div;
  }
};

/* ── PWA Install ───────────────────────────────────────────────────────── */
let deferredPrompt = null;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const banner = document.getElementById('pwa-install-banner');
  if (banner && !localStorage.getItem('pwa_dismissed')) {
    banner.classList.remove('d-none');
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const installBtn  = document.getElementById('pwa-install-btn');
  const dismissBtn  = document.getElementById('pwa-dismiss-btn');

  if (installBtn) {
    installBtn.addEventListener('click', async () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        deferredPrompt = null;
        document.getElementById('pwa-install-banner')?.classList.add('d-none');
      }
    });
  }

  if (dismissBtn) {
    dismissBtn.addEventListener('click', () => {
      localStorage.setItem('pwa_dismissed', '1');
      document.getElementById('pwa-install-banner')?.classList.add('d-none');
    });
  }
});

/* ── Init ──────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
  SidebarManager.init();
  AutoFilterManager.init();

  // Theme toggle button
  document.querySelectorAll('.theme-toggle').forEach((button) => {
    button.addEventListener('click', () => ThemeManager.toggle());
  });

  // Auto-dismiss alerts after 5s
  document.querySelectorAll('.alert.alert-success').forEach(el => {
    setTimeout(() => {
      const alert = bootstrap.Alert.getOrCreateInstance(el);
      alert?.close();
    }, 5000);
  });

  // Date input — set today as default if empty
  document.querySelectorAll('input[type="date"]').forEach(input => {
    if (!input.value && !input.dataset.noDefault) {
      const today = new Date().toISOString().split('T')[0];
      if (input.name === 'date' || input.name === 'next_due_date' || input.name === 'start_date') {
        input.value = today;
      }
    }
  });
});
