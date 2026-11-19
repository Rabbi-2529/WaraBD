/* =========================================================
   WaRa BD — store script (Bulletproof Checkout & Contact)
   Final version: bug fixes + empty-catalog handling + debug
   Requires: products.js (sets window.WARA_PRODUCTS)
   ========================================================= */
(function () {
  'use strict';

  /* ---------- URLs ---------- */
  const URLS = {
    home: '/', products: '/products/', portfolio: '/portfolio/', about: '/about/',
    contact: '/contact/', cart: '/cart/', checkout: '/checkout/',
    product: (slug) => '/products/' + encodeURIComponent(slug) + '/',
    orderSuccess: (num) => '/order/success/' + encodeURIComponent(num) + '/',
    orderFailed: '/order/failed/',
    apiCheckout: '/api/checkout/',
    apiContact: '/api/contact/'
  };

  /* ---------- Site settings (DB-injected, with fallback) ---------- */
  const SITE = Object.assign(
    {
      name: 'WaRa BD',
      phone: '+880 1958-666999',
      whatsapp: '8801958666999',
      email: 'info@warabd.com',
      address: 'Dhaka, Bangladesh',
      mapQuery: 'Dhaka, Bangladesh',
      hours: 'Sat - Thu, 10AM - 8PM',
      announcement: 'In stock',
      merchant: { bkash: '01958-666999', nagad: '01958-666999' },
      social: { facebook: '#', instagram: '#', youtube: '#' }
    },
    (window.__WARA__ && window.__WARA__.site) || {}
  );

  /* ---------- Catalog ---------- */
  const CATALOG = (window.WARA_PRODUCTS || []).filter(p => p && p.id);
  const PRODUCTS = {};
  CATALOG.forEach(p => { PRODUCTS[p.id] = p; });

  const FALLBACK_PRODUCT = {
    id: 'placeholder', name: 'WaRa Lock', model: 'FT-SCL029', brand: 'WaRa', category: 'Smart Lock',
    price: 0, oldPrice: 0, stock: 'in-stock', images: [{ src: '', caption: '' }],
    warranty: '1 Year', description: [], specs: [], features: [], applications: {}, faq: []
  };
  const PRODUCT = CATALOG.find(p => p.featured) || CATALOG[0] || FALLBACK_PRODUCT;

  const STOCK = {
    'in-stock':     { label: 'In stock',     buy: true  },
    'out-of-stock': { label: 'Out of stock', buy: false },
    'upcoming':     { label: 'Upcoming',     buy: false }
  };
  const stockOf = p => STOCK[p.stock] || STOCK['in-stock'];

  /* ---------- Delivery (DB-driven with fallback) ---------- */
  const deliveryData = (window.__WARA__ && window.__WARA__.site && window.__WARA__.site.delivery) || {};
  const DELIVERY = {
    inside:  { label: 'Inside Dhaka',  fee: deliveryData.inside?.fee  || 60,  eta: deliveryData.inside?.eta  || '1-2 days' },
    outside: { label: 'Outside Dhaka', fee: deliveryData.outside?.fee || 120, eta: deliveryData.outside?.eta || '2-4 days' }
  };

  const PAYMENTS = { cod: { label: 'Cash on Delivery' }, bkash: { label: 'bKash' }, nagad: { label: 'Nagad' } };
  const MAX_QTY = 20;

  /* Full 64-district list */
  const DISTRICTS = [
    'Bagerhat','Bandarban','Barguna','Barishal','Bhola','Bogura','Brahmanbaria','Chandpur',
    'Chapai Nawabganj','Chattogram','Chuadanga',"Cox's Bazar",'Cumilla','Dhaka','Dinajpur',
    'Faridpur','Feni','Gaibandha','Gazipur','Gopalganj','Habiganj','Jamalpur','Jashore',
    'Jhalokathi','Jhenaidah','Joypurhat','Khagrachhari','Khulna','Kishoreganj','Kurigram',
    'Kushtia','Lakshmipur','Lalmonirhat','Madaripur','Magura','Manikganj','Meherpur',
    'Moulvibazar','Munshiganj','Mymensingh','Naogaon','Narail','Narayanganj','Narsingdi',
    'Natore','Netrokona','Nilphamari','Noakhali','Pabna','Panchagarh','Patuakhali',
    'Pirojpur','Rajbari','Rajshahi','Rangamati','Rangpur','Satkhira','Shariatpur','Sherpur',
    'Sirajganj','Sunamganj','Sylhet','Tangail','Thakurgaon'
  ];

  /* ---------- Debug logging (only on localhost or ?debug) ---------- */
  const DEBUG = (function () {
    try {
      return location.hostname === 'localhost'
        || location.hostname === '127.0.0.1'
        || location.search.indexOf('debug') !== -1;
    } catch (e) { return false; }
  })();
  const dbg = function () {
    if (!DEBUG) return;
    const args = Array.prototype.slice.call(arguments);
    args.unshift('%c[WaRa]', 'color:#d7182a;font-weight:700');
    console.log.apply(console, args);
  };

  dbg('Catalog loaded:', CATALOG.length, 'product(s) from', window.__WARA_PRODUCTS_SOURCE || 'unknown source');

  /* ---------- Helpers ---------- */
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  const money = n => '৳' + Number(n).toLocaleString('en-IN');
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clampQty = n => Math.min(MAX_QTY, Math.max(1, parseInt(n, 10) || 1));
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const params = new URLSearchParams(location.search);
  const waLink = text => 'https://wa.me/' + SITE.whatsapp + (text ? '?text=' + encodeURIComponent(text) : '');
  const fmtDate = iso => new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  const store = {
    get(key, fallback) { try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; } },
    set(key, val) { try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {} },
    remove(key) { try { localStorage.removeItem(key); } catch (e) {} }
  };

  /* ---------- Icons ---------- */
  const ICONS = {
    cart: '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>',
    phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    mail: '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
    pin: '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    check: '<polyline points="20 6 9 17 4 12"/>',
    x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    minus: '<line x1="5" y1="12" x2="19" y2="12"/>',
    trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
    lock: '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    unlock: '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    truck: '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
    refresh: '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>',
    award: '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
    menu: '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    arrow: '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    back: '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    chevron: '<polyline points="6 9 12 15 18 9"/>',
    home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    briefcase: '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    bed: '<path d="M2 4v16"/><path d="M2 8h18a2 2 0 0 1 2 2v10"/><path d="M2 17h20"/><path d="M6 8v9"/>',
    hospital: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 8v8M8 12h8"/>',
    bag: '<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>',
    box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    archive: '<polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/>',
    drawer: '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="10" y1="7.5" x2="14" y2="7.5"/><line x1="10" y1="16.5" x2="14" y2="16.5"/>',
    grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    message: '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
    facebook: '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>',
    instagram: '<rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>',
    youtube: '<path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"/><polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"/>',
    alert: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    printer: '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    cash: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 12h.01M18 12h.01"/>',
    headset: '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',
    zoom: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>',
    info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    wifioff: '<line x1="1" y1="1" x2="23" y2="23"/><path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55M5 12.55a10.94 10.94 0 0 1 5.17-2.39M10.71 5.05A16 16 0 0 1 22.58 9M1.42 9a15.91 15.91 0 0 1 4.7-2.88M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>',
    send: '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>'
  };
  const icon = (name, cls) => '<svg class="i' + (cls ? ' ' + cls : '') + '" viewBox="0 0 24 24" aria-hidden="true">' + (ICONS[name] || '') + '</svg>';

  /* ---------- Keypad illustration ---------- */
  function keypadSVG(attrs) {
    const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'];
    const cols = [102, 150, 198];
    const rows = [106, 152, 198, 244];
    const keyMarkup = keys.map((label, i) => {
      const cx = cols[i % 3];
      const cy = rows[Math.floor(i / 3)];
      const star = label === '*';
      return '<g class="key" data-k="' + label + '"><rect x="' + (cx - 21) + '" y="' + (cy - 18) + '" width="42" height="36" rx="12" fill="#1d1d1d" stroke="#3a3a3a" stroke-width="1.5"/>' +
        '<text x="' + cx + '" y="' + (cy + (star ? 10 : 7)) + '" text-anchor="middle" font-family="Arial, sans-serif" font-size="' + (star ? 26 : 20) + '" font-weight="700" fill="#ffffff">' + label + '</text></g>';
    }).join('');
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" ' + (attrs || '') + '>' +
      '<defs><radialGradient id="kpg" cx="40%" cy="30%" r="80%"><stop offset="0" stop-color="#2b2b2b"/><stop offset="1" stop-color="#050505"/></radialGradient></defs>' +
      '<circle cx="150" cy="150" r="146" fill="#111111"/>' +
      '<circle cx="150" cy="150" r="138" fill="url(#kpg)" stroke="#2c2c2c" stroke-width="2"/>' +
      '<text x="150" y="68" text-anchor="middle" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#ffffff">WaRa</text>' +
      '<circle class="kp-led" cx="54" cy="152" r="6" fill="#d7182a"/>' +
      keyMarkup + '</svg>';
  }

  const FALLBACK_IMG = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 500"><rect width="600" height="500" fill="#ffffff"/>' +
    keypadSVG('x="160" y="80" width="280" height="280"') +
    '<text x="300" y="420" text-anchor="middle" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#0f0f0f">Image coming soon</text></svg>'
  );
  window.WARA_FALLBACK = FALLBACK_IMG;

  const productImg = (p, index, cls, extra) => {
    const imgs = (p && p.images) || [];
    const im = imgs[index || 0] || imgs[0] || { src: FALLBACK_IMG, caption: '' };
    return '<img src="' + esc(im.src) + '" alt="' + esc((p ? p.name : '') + (im.caption ? ' — ' + im.caption : '')) + '"' +
      (cls ? ' class="' + cls + '"' : '') + ' loading="lazy" onerror="this.onerror=null;this.src=window.WARA_FALLBACK"' + (extra || '') + '>';
  };
  const imgTag = (index, cls, extra) => productImg(PRODUCT, index, cls, extra);
  const productUrl = p => URLS.product(p.id || p.slug);

  /* ---------- Cart ---------- */
  const Cart = {
    KEY: 'wara_cart',
    items() {
      const raw = store.get(this.KEY, []);
      return Array.isArray(raw)
        ? raw.filter(i => PRODUCTS[i.id] && i.qty > 0).map(i => ({ id: i.id, qty: clampQty(i.qty) }))
        : [];
    },
    save(items) {
      store.set(this.KEY, items);
      updateCartBadge(true);
      document.dispatchEvent(new CustomEvent('cart:change'));
    },
    add(id, qty) {
      const items = this.items();
      const it = items.find(i => i.id === id);
      const before = it ? it.qty : 0;
      const after = Math.min(MAX_QTY, before + qty);
      if (it) it.qty = after; else items.push({ id, qty: after });
      this.save(items);
      return after - before;
    },
    setQty(id, qty) {
      const items = this.items();
      const it = items.find(i => i.id === id);
      if (it) it.qty = clampQty(qty); else items.push({ id, qty: clampQty(qty) });
      this.save(items);
    },
    remove(id) { this.save(this.items().filter(i => i.id !== id)); },
    restore(items) { this.save(items); },
    clear() { this.save([]); },
    count() { return this.items().reduce((s, i) => s + i.qty, 0); },
    totals(zone) {
      const lines = this.items().map(i => {
        const p = PRODUCTS[i.id];
        return { id: i.id, qty: i.qty, product: p, total: p.price * i.qty, oldTotal: (p.oldPrice || p.price) * i.qty };
      });
      const subtotal = lines.reduce((s, l) => s + l.total, 0);
      const oldTotal = lines.reduce((s, l) => s + l.oldTotal, 0);
      const delivery = zone && DELIVERY[zone] && lines.length ? DELIVERY[zone].fee : 0;
      return { lines, count: lines.reduce((s, l) => s + l.qty, 0), subtotal, savings: oldTotal - subtotal, delivery, total: subtotal + delivery };
    }
  };

  function updateCartBadge(bump) {
    $$('.cart-count').forEach(el => {
      el.textContent = Cart.count();
      if (bump) { el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump'); }
    });
  }

  /* ---------- Toasts ---------- */
  function toast(msg, opts) {
    opts = opts || {};
    let stack = $('.toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'toast-stack';
      stack.setAttribute('aria-live', 'polite');
      document.body.appendChild(stack);
    }
    const el = document.createElement('div');
    el.className = 'toast' + (opts.type === 'error' ? ' error' : '');
    el.innerHTML = '<span class="t-icon">' + icon(opts.type === 'error' ? 'x' : 'check') + '</span><span>' + msg + '</span>' +
      (opts.href ? '<a href="' + opts.href + '">' + opts.linkText + '</a>' : '') +
      (opts.onAction ? '<a href="#" data-act>' + opts.actionText + '</a>' : '');
    if (opts.onAction) el.querySelector('[data-act]').addEventListener('click', e => { e.preventDefault(); opts.onAction(); close(); });
    stack.appendChild(el);
    function close() { el.classList.add('out'); setTimeout(() => el.remove(), 300); }
    setTimeout(close, opts.duration || 3800);
  }

  /* ---------- Layout ---------- */
  const NAV = [[URLS.home, 'Home', 'home'], [URLS.products, 'Products', 'products'], [URLS.portfolio, 'Portfolio', 'portfolio'], [URLS.about, 'About Us', 'about'], [URLS.contact, 'Contact', 'contact']];
  const logoHTML = '<a class="logo" href="' + URLS.home + '" aria-label="WaRa BD home"><span class="logo-mark">' + icon('lock') + '</span><span><span class="wa">Wa</span><span class="ra">Ra</span></span><small>BD</small></a>';

  function renderLayout() {
    const page = document.body.dataset.page;
    const header = $('#site-header');
    if (header) {
      header.outerHTML =
        '<div class="topbar"><div class="container"><div class="topbar-group"><span><span class="dot"></span>' + esc(SITE.announcement) + '</span></div>' +
        '<div class="topbar-group"><a href="tel:' + SITE.phone.replace(/[^\d+]/g, '') + '">' + icon('phone') + esc(SITE.phone) + '</a>' +
        '<a class="hide-sm" href="mailto:' + SITE.email + '">' + icon('mail') + esc(SITE.email) + '</a></div></div></div>' +
        '<header class="site-header" id="siteHeader"><div class="container nav">' + logoHTML +
        '<nav class="nav-links" id="navLinks" aria-label="Main">' +
        NAV.map(n => '<a href="' + n[0] + '"' + (n[2] === page || (n[2] === 'products' && page === 'product') ? ' class="active" aria-current="page"' : '') + '>' + n[1] + '</a>').join('') +
        '</nav><div class="nav-actions"><a class="btn btn-red btn-sm hide-sm" href="' + URLS.products + '">Shop Now</a>' +
        '<a class="cart-btn" href="' + URLS.cart + '" aria-label="Shopping cart">' + icon('cart') + '<span class="cart-count">0</span></a>' +
        '<button class="menu-toggle" id="menuToggle" aria-label="Open menu" aria-expanded="false" aria-controls="navLinks">' + icon('menu') + '</button></div></div></header>';
    }

    const footer = $('#site-footer');
    if (footer) {
      footer.outerHTML =
        '<footer class="site-footer"><div class="container footer-grid"><div>' + logoHTML +
        '<p>Smart, keyless security products from WaRa — genuine items with official warranty and support across Bangladesh.</p>' +
        '<div class="socials"><a href="' + SITE.social.facebook + '" aria-label="Facebook">' + icon('facebook') + '</a>' +
        '<a href="' + SITE.social.instagram + '" aria-label="Instagram">' + icon('instagram') + '</a>' +
        '<a href="' + SITE.social.youtube + '" aria-label="YouTube">' + icon('youtube') + '</a></div></div>' +
        '<div><h4>Shop</h4><ul class="footer-links"><li><a href="' + URLS.products + '">All products</a></li>' +
        '<li><a href="' + productUrl(PRODUCT) + '">' + esc(PRODUCT.model) + ' details</a></li>' +
        '<li><a href="' + URLS.portfolio + '">Product portfolio</a></li>' +
        '<li><a href="' + URLS.cart + '">Shopping cart</a></li>' +
        '<li><a href="' + URLS.checkout + '">Checkout</a></li></ul></div>' +
        '<div><h4>Company</h4><ul class="footer-links"><li><a href="' + URLS.about + '">About us</a></li>' +
        '<li><a href="' + URLS.contact + '">Contact us</a></li>' +
        '<li><a href="' + productUrl(PRODUCT) + '#faq">FAQ</a></li>' +
        '<li><a href="' + productUrl(PRODUCT) + '#warranty">Warranty & delivery</a></li></ul></div>' +
        '<div><h4>Get in touch</h4><ul class="footer-contact">' +
        '<li>' + icon('pin') + '<span>' + esc(SITE.address) + '</span></li>' +
        '<li>' + icon('phone') + '<a href="tel:' + SITE.phone.replace(/[^\d+]/g, '') + '">' + esc(SITE.phone) + '</a></li>' +
        '<li>' + icon('mail') + '<a href="mailto:' + SITE.email + '">' + esc(SITE.email) + '</a></li>' +
        '<li>' + icon('clock') + '<span>' + esc(SITE.hours) + '</span></li></ul></div></div>' +
        '<div class="footer-bottom"><div class="container"><span>© ' + new Date().getFullYear() + ' ' + esc(SITE.name) + '. All rights reserved.</span>' +
        '<span class="pay-chips"><span>Cash on Delivery</span><span>bKash</span><span>Nagad</span></span></div></div></footer>' +
        '<a class="wa-float" href="' + waLink('Hi WaRa BD, I have a question about your products.') + '" target="_blank" rel="noopener" aria-label="Chat on WhatsApp">' + icon('message') + '</a>';
    }

    const toggle = $('#menuToggle');
    if (toggle) toggle.addEventListener('click', () => {
      const open = $('#navLinks').classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
      toggle.innerHTML = icon(open ? 'x' : 'menu');
    });
    const siteHeader = $('#siteHeader');
    if (siteHeader) {
      const onScroll = () => siteHeader.classList.toggle('scrolled', window.scrollY > 10);
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    }
    updateCartBadge(false);
  }

  function bindContent(root) {
    root = root || document;
    const save = (PRODUCT.oldPrice || PRODUCT.price) - PRODUCT.price;
    const values = {
      'price': money(PRODUCT.price), 'old-price': money(PRODUCT.oldPrice),
      'save': money(save), 'save-pct': Math.round(save / PRODUCT.oldPrice * 100) + '%',
      'name': PRODUCT.name, 'subtitle': PRODUCT.subtitle, 'model': PRODUCT.model,
      'sku': PRODUCT.sku, 'warranty': PRODUCT.warranty, 'phone': SITE.phone,
      'email': SITE.email, 'address': SITE.address, 'hours': SITE.hours,
      'inside-fee': money(DELIVERY.inside.fee), 'outside-fee': money(DELIVERY.outside.fee),
      'inside-eta': DELIVERY.inside.eta, 'outside-eta': DELIVERY.outside.eta, 'max-qty': MAX_QTY
    };
    $$('[data-bind]', root).forEach(el => { if (values[el.dataset.bind] != null) el.textContent = values[el.dataset.bind]; });
    $$('[data-href]', root).forEach(el => {
      const t = el.dataset.href;
      if (t === 'tel') el.href = 'tel:' + SITE.phone.replace(/[^\d+]/g, '');
      if (t === 'mail') el.href = 'mailto:' + SITE.email;
      if (t === 'wa') {
        el.href = waLink(el.dataset.waText || 'Hi WaRa BD, I want to place an order.');
        el.target = '_blank'; el.rel = 'noopener';
      }
    });
    $$('[data-icon]', root).forEach(el => { el.outerHTML = icon(el.dataset.icon, el.className); });
    $$('img[data-pimg]', root).forEach(el => {
      const im = PRODUCT.images[+el.dataset.pimg] || PRODUCT.images[0] || { src: FALLBACK_IMG };
      el.onerror = () => { el.onerror = null; el.src = FALLBACK_IMG; };
      el.src = im.src;
      if (!el.alt) el.alt = PRODUCT.name + ' — ' + im.caption;
    });
    $$('[data-qty-mount]', root).forEach(el => { el.outerHTML = qtyHTML(1, el.dataset.size, el.id); });
  }

  function qtyHTML(value, size, id) {
    const v = clampQty(value);
    return '<div class="qty' + (size ? ' ' + size : '') + '"' + (id ? ' id="' + id + '"' : '') + '>' +
      '<button type="button" data-step="-1" aria-label="Decrease quantity"' + (v <= 1 ? ' disabled' : '') + '>' + icon('minus') + '</button>' +
      '<input type="number" inputmode="numeric" min="1" max="' + MAX_QTY + '" value="' + v + '" aria-label="Quantity">' +
      '<button type="button" data-step="1" aria-label="Increase quantity"' + (v >= MAX_QTY ? ' disabled' : '') + '>' + icon('plus') + '</button></div>';
  }

  function syncQty(wrap) {
    const input = $('input', wrap);
    const v = clampQty(input.value);
    input.value = v;
    $('[data-step="-1"]', wrap).disabled = v <= 1;
    $('[data-step="1"]', wrap).disabled = v >= MAX_QTY;
    return v;
  }
  function scopeQty(el) {
    const scope = el.closest('[data-buy-scope]');
    const input = scope && $('.qty input', scope);
    return input ? clampQty(input.value) : 1;
  }
  function scopeProduct(el) {
    const scope = el.closest('[data-buy-scope]');
    const id = el.dataset.id || (scope && scope.dataset.id) || (PRODUCT && PRODUCT.id);
    return PRODUCTS[id];
  }

  /* ---------- Global events ---------- */
  function initGlobalEvents() {
    document.addEventListener('change', e => {
      const wrap = e.target.closest && e.target.closest('.qty');
      if (wrap && e.target.tagName === 'INPUT') syncQty(wrap);
    }, true);

    document.addEventListener('click', e => {
      const step = e.target.closest('.qty [data-step]');
      if (step) {
        const wrap = step.closest('.qty');
        const input = $('input', wrap);
        const next = (parseInt(input.value, 10) || 1) + Number(step.dataset.step);
        if (next > MAX_QTY) { toast('Maximum ' + MAX_QTY + ' units per order.', { type: 'error' }); return; }
        input.value = clampQty(next);
        syncQty(wrap);
        input.dispatchEvent(new Event('change', { bubbles: true }));
        return;
      }

      const add = e.target.closest('[data-add-to-cart]');
      if (add) {
        e.preventDefault();
        const scope = add.closest('[data-buy-scope]');
        const id = add.dataset.id || (scope && scope.dataset.id) || (PRODUCT && PRODUCT.id);
        const p = PRODUCTS[id];

        if (!p || !stockOf(p).buy) { toast('Not available.', { type: 'error' }); return; }

        const qtyInput = scope ? $('.qty input', scope) : null;
        const qty = qtyInput ? clampQty(qtyInput.value) : 1;

        const added = Cart.add(p.id, qty);
        if (!added) { toast('Cart has max units.', { type: 'error', href: URLS.cart, linkText: 'View cart' }); return; }

        toast(added + ' × ' + esc(p.model) + ' added to cart', { href: URLS.cart, linkText: 'View cart' });
        const label = add.innerHTML;
        add.innerHTML = icon('check') + ' Added';
        add.disabled = true;
        setTimeout(() => { add.innerHTML = label; add.disabled = false; }, 1400);
        return;
      }

      const buy = e.target.closest('[data-buy-now]');
      if (buy) {
        e.preventDefault();
        const scope = buy.closest('[data-buy-scope]');
        const id = buy.dataset.id || (scope && scope.dataset.id) || (PRODUCT && PRODUCT.id);
        const p = PRODUCTS[id];

        if (!p || !stockOf(p).buy) { toast('Not available.', { type: 'error' }); return; }

        const qtyInput = scope ? $('.qty input', scope) : null;
        const qty = qtyInput ? clampQty(qtyInput.value) : 1;

        Cart.setQty(p.id, qty);
        location.href = URLS.checkout;
        return;
      }

      const faq = e.target.closest('.faq-q');
      if (faq) {
        const item = faq.closest('.faq-item');
        const open = item.classList.toggle('open');
        faq.setAttribute('aria-expanded', open);
      }
    });
  }

  /* ---------- Reveal on scroll ---------- */
  function initReveal() {
    const items = $$('.reveal');
    if (!('IntersectionObserver' in window)) { items.forEach(el => el.classList.add('in')); return; }
    const io = new IntersectionObserver(entries => {
      entries.forEach(en => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    items.forEach(el => io.observe(el));
  }

  /* ---------- Lightbox ---------- */
  let lbIndex = 0; let lbImages = [];
  function openLightbox(images, index) {
    lbImages = images && images.length ? images : [{ src: FALLBACK_IMG, caption: '' }];
    let lb = $('#lightbox');
    if (!lb) {
      lb = document.createElement('div');
      lb.id = 'lightbox';
      lb.className = 'lightbox';
      lb.setAttribute('role', 'dialog');
      lb.setAttribute('aria-modal', 'true');
      lb.innerHTML = '<button class="lb-close" aria-label="Close">' + icon('x') + '</button>' +
        '<button class="gallery-nav prev" aria-label="Previous image">' + icon('arrow') + '</button>' +
        '<img alt="">' +
        '<button class="gallery-nav next" aria-label="Next image">' + icon('arrow') + '</button>' +
        '<div class="lb-cap"></div>';
      document.body.appendChild(lb);
      lb.addEventListener('click', e => {
        if (e.target === lb || e.target.closest('.lb-close')) closeLightbox();
        else if (e.target.closest('.prev')) showLb(lbIndex - 1);
        else if (e.target.closest('.next')) showLb(lbIndex + 1);
      });
      document.addEventListener('keydown', e => {
        if (!lb.classList.contains('open')) return;
        if (e.key === 'Escape') closeLightbox();
        if (e.key === 'ArrowLeft') showLb(lbIndex - 1);
        if (e.key === 'ArrowRight') showLb(lbIndex + 1);
      });
    }
    lb.classList.add('open');
    document.body.style.overflow = 'hidden';
    showLb(index);
    $('.lb-close', lb).focus();
  }
  function showLb(i) {
    const n = lbImages.length;
    lbIndex = (i + n) % n;
    const lb = $('#lightbox');
    const img = $('img', lb);
    img.onerror = () => { img.onerror = null; img.src = FALLBACK_IMG; };
    img.src = lbImages[lbIndex].src;
    img.alt = lbImages[lbIndex].caption;
    $('.lb-cap', lb).textContent = (lbIndex + 1) + ' / ' + n + (lbImages[lbIndex].caption ? ' — ' + lbImages[lbIndex].caption : '');
  }
  function closeLightbox() {
    $('#lightbox').classList.remove('open');
    document.body.style.overflow = '';
  }

  /* ---------- Totals / empty helpers ---------- */
  function totalsHTML(t, deliveryText) {
    return '<div class="sum-row"><span>Subtotal (' + t.count + ' item' + (t.count === 1 ? '' : 's') + ')</span><span>' + money(t.subtotal) + '</span></div>' +
      (t.savings > 0 ? '<div class="sum-row save"><span>You save</span><span>− ' + money(t.savings) + '</span></div>' : '') +
      '<div class="sum-row"><span>Delivery</span><span>' + (deliveryText || money(t.delivery)) + '</span></div>' +
      '<div class="sum-row total"><span>Total</span><span>' + money(t.total) + '</span></div>';
  }
  function emptyCartHTML(title, text) {
    return '<div class="empty-state"><div class="big-icon">' + icon('cart') + '</div>' +
      '<h2>' + (title || 'Your cart is empty') + '</h2>' +
      '<p>' + (text || 'Browse our WaRa products and add your favourites to the cart.') + '</p>' +
      '<a class="btn btn-red" href="' + URLS.products + '">' + icon('bag') + ' Browse products</a></div>';
  }

  /* =========================================================
     Page Initializers
     ========================================================= */

  function initHome() {
    const shelf = $('#homeProducts');
    if (shelf) shelf.innerHTML = CATALOG.slice(0, 4).map(productCardHTML).join('') + comingSoonHTML();
    const wrap = $('#heroKeypad');
    if (!wrap) return;
    wrap.innerHTML = keypadSVG('role="img" aria-label="WaRa FT-SCL029 keypad"');
    const status = $('#lockStatus');
    const label = $('b', status);
    const led = $('.kp-led', wrap);
    const keyEl = k => $('.key[data-k="' + k + '"]', wrap);
    const setState = (text, ok) => {
      label.textContent = text;
      status.classList.toggle('ok', ok);
      led.setAttribute('fill', ok ? '#12924a' : '#d7182a');
    };
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setState('Locked', false); return; }
    const code = ['2', '5', '8', '0', '#'];
    (async function loop() {
      for (;;) {
        setState('Locked', false);
        await wait(1600);
        setState('Entering code…', false);
        for (const k of code) {
          keyEl(k).classList.add('pressed');
          await wait(230);
          keyEl(k).classList.remove('pressed');
          await wait(170);
        }
        $$('.key', wrap).forEach(el => el.classList.add('ok'));
        setState('Unlocked', true);
        await wait(380);
        $$('.key', wrap).forEach(el => el.classList.remove('ok'));
        await wait(2400);
      }
    })();
  }

  function productCardHTML(p) {
    const st = stockOf(p);
    const save = p.oldPrice > p.price ? p.oldPrice - p.price : 0;
    return '<article class="p-card" data-buy-scope data-id="' + esc(p.id) + '">' +
      '<a class="p-card-media" href="' + productUrl(p) + '">' + productImg(p, 0) +
      (save ? '<span class="p-card-badge">' + money(save) + ' Off</span>' : '') +
      (st.buy ? '' : '<span class="p-card-badge stock-out">' + st.label + '</span>') + '</a>' +
      '<div class="p-card-body"><span class="p-card-cat">' + esc(p.brand) + ' · ' + esc(p.category) + '</span>' +
      '<h3><a href="' + productUrl(p) + '">' + esc(p.name) + '</a></h3>' +
      '<div class="p-card-price"><strong>' + money(p.price) + '</strong>' + (save ? '<s>' + money(p.oldPrice) + '</s>' : '') + '</div>' +
      '<div class="p-card-actions">' +
      (st.buy
        ? '<button type="button" class="btn btn-green" data-add-to-cart>' + icon('cart') + ' Add to Cart</button>' +
          '<button type="button" class="btn btn-red" data-buy-now>Buy Now</button>'
        : '<a class="btn btn-outline" href="' + productUrl(p) + '">View details</a>') +
      '</div></div></article>';
  }

  function comingSoonHTML() {
    if (CATALOG.length >= 4) return '';
    return '<div class="p-card soon"><div class="icon-box green">' + icon('box') + '</div>' +
      '<h3>More WaRa products coming soon</h3>' +
      '<p>New smart security products are on the way. Message us to hear first when they arrive.</p>' +
      '<a class="link-arrow" target="_blank" rel="noopener" href="' + waLink('Hi WaRa BD, please let me know when new products arrive.') + '">Get notified ' + icon('arrow') + '</a></div>';
  }

  function initProducts() {
    const grid = $('#productGrid');
    const sidebar = $('#shopSidebar');
    const minR = $('#fMin');
    const maxR = $('#fMax');
    const minN = $('#fMinNum');
    const maxN = $('#fMaxNum');
    const fill = $('.range-fill', sidebar);
    const search = $('#fSearch');
    const sortSel = $('#fSort');
    if (!grid || !sidebar) return;

    /* Empty catalog — show clear message, skip filter setup */
    if (!CATALOG.length) {
      dbg('Empty catalog — check products.js bridge and Django admin.');
      grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="big-icon">' + icon('box') + '</div>' +
        '<h2>No products yet</h2><p>Products added in the admin panel will appear here.</p></div>';
      return;
    }

    const prices = CATALOG.map(p => p.price);
    const floor = prices.length ? Math.floor(Math.min.apply(null, prices) / 500) * 500 : 0;
    let ceil = prices.length ? Math.ceil(Math.max.apply(null, prices) / 500) * 500 : 1000;
    if (ceil <= floor) ceil = floor + 500;
    if (minR) [minR, maxR, minN, maxN].forEach(el => { el.min = floor; el.max = ceil; el.step = 50; });

    const optHTML = (group, value, label, n) => '<label class="filter-opt"><span><input type="checkbox" name="' + group + '" value="' + esc(value) + '"> ' + esc(label) + '</span><span class="count">' + n + '</span></label>';
    const cats = Array.from(new Set(CATALOG.map(p => p.category)));
    if ($('#fCats')) $('#fCats').innerHTML = cats.map(c => optHTML('cat', c, c, CATALOG.filter(p => p.category === c).length)).join('');
    if ($('#fStock')) $('#fStock').innerHTML = Object.keys(STOCK).map(k => optHTML('stock', k, STOCK[k].label, CATALOG.filter(p => (p.stock || 'in-stock') === k).length)).join('');

    const qCat = params.get('category');
    if (qCat && sidebar) $$('input[name="cat"]', sidebar).forEach(i => { i.checked = i.value === qCat; });
    if (params.get('q') && search) search.value = params.get('q');

    const clampNum = (v, a, b) => Math.min(b, Math.max(a, Number(v) || 0));
    function syncRange(src) {
      if (!minR) return;
      const fromNum = src === minN || src === maxN;
      let lo = fromNum ? clampNum(minN.value, floor, ceil) : Number(minR.value);
      let hi = fromNum ? clampNum(maxN.value, floor, ceil) : Number(maxR.value);
      if (lo > hi) { if (src === minR || src === minN) lo = hi; else hi = lo; }
      minR.value = minN.value = lo;
      maxR.value = maxN.value = hi;
      if (fill) {
        fill.style.left = ((lo - floor) / (ceil - floor) * 100) + '%';
        fill.style.right = ((ceil - hi) / (ceil - floor) * 100) + '%';
      }
      minR.style.zIndex = lo >= ceil ? 3 : '';
    }

    const SORTS = {
      'price-asc': (a, b) => a.price - b.price,
      'price-desc': (a, b) => b.price - a.price,
      'name': (a, b) => a.name.localeCompare(b.name),
      'newest': (a, b) => String(b.added || '').localeCompare(String(a.added || ''))
    };

    function render() {
      const lo = minR ? Number(minR.value) : floor;
      const hi = maxR ? Number(maxR.value) : ceil;
      const q = search ? search.value.trim().toLowerCase() : '';
      const catSel = sidebar ? $$('input[name="cat"]:checked', sidebar).map(i => i.value) : [];
      const stockSel = sidebar ? $$('input[name="stock"]:checked', sidebar).map(i => i.value) : [];
      let list = CATALOG.filter(p =>
        p.price >= lo && p.price <= hi &&
        (!catSel.length || catSel.includes(p.category)) &&
        (!stockSel.length || stockSel.includes(p.stock || 'in-stock')) &&
        (!q || [p.name, p.subtitle, p.model, p.brand, p.category].join(' ').toLowerCase().includes(q))
      );
      if (sortSel && SORTS[sortSel.value]) list = list.slice().sort(SORTS[sortSel.value]);
      if ($('#shopCount')) $('#shopCount').innerHTML = 'Showing <b>' + list.length + '</b> of <b>' + CATALOG.length + '</b> product' + (CATALOG.length === 1 ? '' : 's');
      if (!list.length) {
        grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="big-icon">' + icon('zoom') + '</div><h2>No products match your filters</h2><p>Try a wider price range or clear the filters.</p><button type="button" class="btn btn-red" data-reset-filters>Reset filters</button></div>';
        return;
      }
      grid.innerHTML = list.map(productCardHTML).join('') + comingSoonHTML();
    }

    function reset() {
      if (minR) { minR.value = floor; maxR.value = ceil; syncRange(minR); }
      if (search) search.value = '';
      if (sidebar) $$('input[type="checkbox"]', sidebar).forEach(i => { i.checked = false; });
      if (sortSel) sortSel.value = 'default';
      render();
    }

    if (minR) {
      [minR, maxR].forEach(el => el.addEventListener('input', () => { syncRange(el); render(); }));
      [minN, maxN].forEach(el => el.addEventListener('change', () => { syncRange(el); render(); }));
    }
    if (sidebar) sidebar.addEventListener('change', e => { if (e.target.type === 'checkbox') render(); });
    if (search) search.addEventListener('input', render);
    if (sortSel) sortSel.addEventListener('change', render);
    if ($('#fReset')) $('#fReset').addEventListener('click', reset);
    if (grid) grid.addEventListener('click', e => { if (e.target.closest('[data-reset-filters]')) reset(); });
    if ($('#filterToggle')) $('#filterToggle').addEventListener('click', () => {
      const open = sidebar.classList.toggle('open');
      $('#filterToggle').setAttribute('aria-expanded', String(open));
    });

    if (minR) { minR.value = floor; maxR.value = ceil; syncRange(minR); }
    render();
  }

  /* ---------- Product page ---------- */
  function initProduct() {
    const mount = $('#productMount');
    if (!mount) return;
    const pathMatch = location.pathname.match(/^\/products\/([^/]+)\/?$/);
    const wanted = params.get('id') || (pathMatch ? decodeURIComponent(pathMatch[1]) : null);
    const p = wanted ? PRODUCTS[wanted] : PRODUCT;
    if (!p) {
      mount.innerHTML = '<div class="section text-center"><h2>Product not found</h2></div>';
      return;
    }

    const st = stockOf(p);
    const save = p.oldPrice > p.price ? p.oldPrice - p.price : 0;
    const pct = save ? Math.round(save / p.oldPrice * 100) : 0;
    const images = p.images && p.images.length ? p.images : [{ src: FALLBACK_IMG, caption: '' }];

    mount.innerHTML = '<section class="section" style="padding-top:44px"><div class="container">' +
      '<div class="row">' +
        '<div class="col-md-6">' +
          '<div class="gallery-main" id="gMain">' +
            (pct ? '<span class="gallery-badge">Save ' + pct + '%</span>' : '') +
            productImg(p, 0, '', ' id="gMainImg"') +
          '</div>' +
          (images.length > 1 ? '<div class="thumbs" id="gThumbs">' + images.map((im, i) =>
            '<button type="button" data-i="' + i + '"' + (i === 0 ? ' class="active"' : '') + ' aria-label="View image ' + (i + 1) + '">' + productImg(p, i) + '</button>'
          ).join('') + '</div>' : '') +
        '</div>' +
        '<div class="col-md-6" data-buy-scope data-id="' + esc(p.id) + '">' +
          '<h1 class="p-title">' + esc(p.name) + '</h1>' +
          '<div class="p-price"><span class="price-now">' + money(p.price) + '</span>' +
            (save ? '<span class="price-old">' + money(p.oldPrice) + '</span><span class="price-save">Save ' + money(save) + '</span>' : '') +
          '</div>' +
          (p.short ? '<p class="p-short">' + esc(p.short) + '</p>' : '') +
          (st.buy ? '<div class="buy-row" id="buyRow">' + qtyHTML(1) +
            '<button type="button" class="btn btn-green" data-add-to-cart>' + icon('cart') + ' Add to Cart</button></div>' : '') +
        '</div>' +
      '</div>' +
    '</div></section>';

    bindContent(mount);

    const main = $('#gMain');
    const thumbs = $('#gThumbs');
    let current = 0;
    const show = i => {
      current = (i + images.length) % images.length;
      const img = $('#gMainImg');
      if (img) img.src = images[current].src;
      if (thumbs) $$('button', thumbs).forEach((b, bi) => b.classList.toggle('active', bi === current));
    };
    if (thumbs) {
      thumbs.addEventListener('click', e => {
        const b = e.target.closest('button');
        if (b) show(+b.dataset.i);
      });
    }
    if (main) main.addEventListener('click', () => openLightbox(images, current));
  }

  /* ---------- Portfolio ---------- */
  const USE_CASES = (window.__WARA__ && window.__WARA__.useCases && window.__WARA__.useCases.length > 0)
    ? window.__WARA__.useCases
    : [{ cat: 'home', icon: 'archive', tone: '', title: 'Bedroom Wardrobes', place: 'Homes & apartments', mode: 'private', text: 'Keep jewellery, cash and documents behind a code only your family knows.' }];
  const CATS = { all: 'All', home: 'Home', office: 'Office', hospitality: 'Hospitality & Health', public: 'Public Spaces', commercial: 'Commercial' };

  function initPortfolio() {
    const pg = $('#photoGrid');
    if (!pg) return;
    pg.innerHTML = PRODUCT.images.map((im, i) =>
      '<figure data-i="' + i + '" tabindex="0" role="button" aria-label="Enlarge: ' + esc(im.caption) + '">' +
      imgTag(i) + '<figcaption><span>' + esc(im.caption) + '</span>' + icon('zoom') + '</figcaption></figure>'
    ).join('');
    pg.addEventListener('click', e => {
      const f = e.target.closest('figure');
      if (f) openLightbox(PRODUCT.images, +f.dataset.i);
    });
    pg.addEventListener('keydown', e => {
      const f = e.target.closest('figure');
      if (f && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        openLightbox(PRODUCT.images, +f.dataset.i);
      }
    });

    const pF = $('#pfFilters');
    if (pF) pF.innerHTML = Object.keys(CATS).map(k =>
      '<button type="button" data-f="' + k + '"' + (k === 'all' ? ' class="active"' : '') + '>' + CATS[k] + '</button>'
    ).join('');
    const pG = $('#pfGrid');
    if (pG) pG.innerHTML = USE_CASES.map(u =>
      '<article class="pf-card" data-cat="' + u.cat + '"><div class="pf-visual ' + u.tone + '"><span class="pf-cat">' + CATS[u.cat] + '</span>' + icon(u.icon, 'big') + '</div><div class="pf-body"><h3>' + u.title + '</h3><p>' + u.text + '</p><span class="pf-mode' + (u.mode === 'public' ? ' red' : '') + '">' + icon(u.mode === 'public' ? 'users' : 'user') + (u.mode === 'public' ? 'Public (visitor) mode' : 'Private mode') + ' · ' + u.place + '</span></div></article>'
    ).join('');

    if (pF) pF.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) return;
      $$('#pfFilters button').forEach(x => x.classList.toggle('active', x === b));
      $$('#pfGrid .pf-card').forEach(c => c.classList.toggle('hide', b.dataset.f !== 'all' && c.dataset.cat !== b.dataset.f));
    });
  }

  /* ---------- Contact ---------- */
  const RULES = {
    name: v => v.trim().length >= 3 || 'Please enter your full name.',
    phone: v => /^(?:\+?88)?01[3-9]\d{8}$/.test(v.replace(/[\s-]/g, '')) || 'Enter a valid Bangladeshi mobile number.',
    email: v => !v.trim() || /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) || 'Enter a valid email address.',
    address: v => v.trim().length >= 10 || 'Please enter your full address.',
    required: v => v.trim().length > 0 || 'This field is required.',
    choice: v => v.trim().length > 0 || 'Please select an option.',
    message: v => v.trim().length >= 10 || 'Please write at least 10 characters.',
    trx: v => /^[A-Za-z0-9]{6,}$/.test(v.trim()) || 'Enter the transaction ID from your payment SMS.'
  };

  function checkField(input) {
    const rule = RULES[input.dataset.rule];
    const wrap = input.closest('.field');
    if (!rule || !wrap) return true;
    if (input.offsetParent === null) { wrap.classList.remove('invalid'); return true; }
    const res = rule(input.value);
    const ok = res === true;
    wrap.classList.toggle('invalid', !ok);
    input.setAttribute('aria-invalid', String(!ok));
    let err = $('.err', wrap);
    if (!err) { err = document.createElement('div'); err.className = 'err'; wrap.appendChild(err); }
    err.textContent = ok ? '' : res;
    return ok;
  }
  function validateForm(form) {
    let first = null;
    $$('[data-rule]', form).forEach(i => { if (!checkField(i) && !first) first = i; });
    return first;
  }
  function liveValidate(form) {
    form.addEventListener('input', e => {
      if (e.target.dataset.rule && e.target.closest('.field.invalid')) checkField(e.target);
    });
    form.addEventListener('focusout', e => {
      if (e.target.dataset && e.target.dataset.rule && e.target.value.trim()) checkField(e.target);
    });
  }

  function initContact() {
    const form = $('#contactForm');
    const map = $('#mapFrame');
    if (map) map.src = 'https://www.google.com/maps?q=' + encodeURIComponent(SITE.mapQuery) + '&output=embed';
    if (!form) return;

    const successHeading = $('#contactSuccess h2');
    if (successHeading && !successHeading.hasAttribute('tabindex')) {
      successHeading.setAttribute('tabindex', '-1');
    }

    liveValidate(form);

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const bad = validateForm(form);
      if (bad) { bad.focus(); toast('Please fix the highlighted fields.', { type: 'error' }); return; }

      const data = Object.fromEntries(new FormData(form).entries());

      const btn = form.querySelector('button[type="submit"]');
      const originalText = btn.innerHTML;
      btn.innerHTML = 'Sending...';
      btn.disabled = true;

      try {
        const csrfInput = document.querySelector('[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : '';
        const response = await fetch(URLS.apiContact, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
          form.hidden = true;
          const panel = $('#contactSuccess');
          if (panel) {
            panel.classList.add('show');
            const h = $('h2', panel);
            if (h) h.focus();
          }
        } else {
          alert('Error: ' + (result.error || 'Unknown error'));
          btn.innerHTML = originalText;
          btn.disabled = false;
        }
      } catch (err) {
        alert('Network error. Please try again.');
        btn.innerHTML = originalText;
        btn.disabled = false;
      }
    });

    const again = $('#contactAgain');
    if (again) again.addEventListener('click', () => {
      form.reset();
      form.hidden = false;
      const panel = $('#contactSuccess');
      if (panel) panel.classList.remove('show');
      const btn = form.querySelector('button[type="submit"]');
      if (btn) {
        btn.innerHTML = '<i data-icon="send"></i> Send message';
        btn.disabled = false;
      }
      bindContent(form);
    });
  }

  /* ---------- Cart page ---------- */
  function initCart() {
    const mount = $('#cartMount');
    if (!mount) return;
    const summaryHTML = t => '<h3>Order summary</h3>' + totalsHTML(t, 'At checkout') +
      '<a class="btn btn-red btn-block" href="' + URLS.checkout + '">Proceed to checkout ' + icon('arrow') + '</a>' +
      '<p class="summary-note">' + icon('truck') + 'Delivery from ' + money(DELIVERY.inside.fee) + ' · Cash on delivery</p>';
    const render = () => {
      const t = Cart.totals();
      if (!t.lines.length) { mount.innerHTML = emptyCartHTML(); return; }
      mount.innerHTML =
        '<div class="cart-layout"><div><table class="cart-table"><thead><tr><th>Product</th><th>Price</th><th>Quantity</th><th>Total</th><th><span class="sr-only">Remove</span></th></tr></thead><tbody>' +
        t.lines.map(l =>
          '<tr data-id="' + l.id + '"><td><div class="cart-prod"><a href="' + productUrl(l.product) + '">' + productImg(l.product) + '</a>' +
          '<div><h3><a href="' + productUrl(l.product) + '">' + esc(l.product.name) + '</a></h3>' +
          '<span>Model: ' + esc(l.product.model) + (l.product.color ? ' · Color: ' + esc(l.product.color) : '') + '</span></div></div></td>' +
          '<td data-label="Price">' + money(l.product.price) + '</td>' +
          '<td data-label="Quantity">' + qtyHTML(l.qty, 'sm') + '</td>' +
          '<td data-label="Total" class="line-total" data-line-total>' + money(l.total) + '</td>' +
          '<td class="rm"><button type="button" class="remove-btn" data-remove="' + l.id + '" aria-label="Remove">' + icon('trash') + '</button></td></tr>'
        ).join('') +
        '</tbody></table><div class="cart-actions">' +
        '<a class="btn btn-outline" href="' + URLS.products + '">' + icon('back') + ' Continue shopping</a>' +
        '<button type="button" class="btn btn-outline" data-clear-cart>' + icon('trash') + ' Clear cart</button></div></div>' +
        '<aside class="summary" id="cartSummary">' + summaryHTML(t) + '</aside></div>';
    };
    const update = () => {
      const t = Cart.totals();
      const rows = $$('tr[data-id]', mount);
      if (!t.lines.length || rows.length !== t.lines.length) { render(); return; }
      t.lines.forEach(l => {
        const row = $('tr[data-id="' + l.id + '"]', mount);
        if (!row) return;
        $('[data-line-total]', row).textContent = money(l.total);
        const input = $('.qty input', row);
        if (+input.value !== l.qty) { input.value = l.qty; syncQty($('.qty', row)); }
      });
      const summary = $('#cartSummary');
      if (summary) summary.innerHTML = summaryHTML(t);
    };
    mount.addEventListener('change', e => {
      const row = e.target.closest('tr[data-id]');
      if (row && e.target.matches('.qty input')) Cart.setQty(row.dataset.id, e.target.value);
    });
    mount.addEventListener('click', e => {
      const rm = e.target.closest('[data-remove]');
      if (rm) {
        const snapshot = Cart.items();
        Cart.remove(rm.dataset.remove);
        toast('Item removed from cart', { actionText: 'Undo', onAction: () => Cart.restore(snapshot) });
      }
      if (e.target.closest('[data-clear-cart]')) {
        const snapshot = Cart.items();
        Cart.clear();
        toast('Cart cleared', { actionText: 'Undo', onAction: () => Cart.restore(snapshot) });
      }
    });
    document.addEventListener('cart:change', update);
    render();
  }

  /* ---------- Checkout ---------- */
  function initCheckout() {
    const mount = $('#checkoutMount');
    const form = $('#checkoutForm');
    if (!mount || !form) return;

    if (!Cart.count()) {
      mount.innerHTML = emptyCartHTML('Nothing to check out yet', 'Your cart is empty. Add a product first.');
      return;
    }

    const districtEl = $('#coDistrict');
    if (districtEl && districtEl.options.length <= 1) {
      districtEl.insertAdjacentHTML('beforeend', DISTRICTS.map(d => '<option>' + esc(d) + '</option>').join(''));
    }

    const summaryMount = $('#coSummary');
    const zone = () => {
      const el = form.elements.zone;
      if (!el) return 'inside';
      if (el.value !== undefined && el.value !== '') return el.value;
      return 'inside';
    };

    const pay = () => {
      const el = form.elements.payment;
      if (!el) return 'cod';
      const v = el.value;
      return v && PAYMENTS[v] ? v : 'cod';
    };

    const paintSummary = () => {
      if (!summaryMount) return;
      const t = Cart.totals(zone());
      summaryMount.innerHTML = '<h3>Your order</h3>' +
        t.lines.map(l => '<div class="sum-item"><div class="meta"><h4>' + esc(l.product.name) + '</h4><span>Qty: ' + l.qty + '</span></div><div class="price">' + money(l.total) + '</div></div>').join('') +
        '<div class="sum-row"><span>Subtotal</span><span>' + money(t.subtotal) + '</span></div>' +
        '<div class="sum-row"><span>Delivery (' + (DELIVERY[zone()] ? DELIVERY[zone()].label : '') + ')</span><span>' + money(t.delivery) + '</span></div>' +
        '<div class="sum-row total"><span>Total</span><span>' + money(t.total) + '</span></div>' +
        '<button type="submit" class="btn btn-red btn-block mt-3" id="placeOrder">' + icon('lock') + ' Place order · ' + money(t.total) + '</button>';
    };

    paintSummary();

    const zoneEl = form.elements.zone;
    if (zoneEl) {
      const onChange = () => paintSummary();
      if (zoneEl.length !== undefined) {
        $$('input[name="zone"]', form).forEach(r => r.addEventListener('change', onChange));
      } else {
        zoneEl.addEventListener('change', onChange);
      }
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();

      const terms = form.elements.terms;
      if (!terms || !terms.checked) { alert('Please accept the terms & conditions.'); return; }

      const csrfInput = form.querySelector('[name="csrfmiddlewaretoken"]');
      if (!csrfInput) { alert('CSRF Token missing!'); return; }
      const csrfToken = csrfInput.value;

      const payload = {
        name: form.elements.name.value.trim(),
        phone: form.elements.phone.value.trim(),
        email: form.elements.email.value.trim(),
        district: form.elements.district.value,
        address: form.elements.address.value.trim(),
        note: form.elements.note ? form.elements.note.value.trim() : '',
        payment: pay(),
        zone: zone(),
        lines: Cart.items()
      };

      const proc = $('#processing');
      if (proc) proc.classList.add('show');

      try {
        const response = await fetch(URLS.apiCheckout, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (response.ok && result.success) {
          Cart.clear();
          location.href = URLS.orderSuccess(result.order_number);
        } else {
          if (proc) proc.classList.remove('show');
          alert('Checkout Failed: ' + (result.error || 'Unknown error'));
        }
      } catch (err) {
        if (proc) proc.classList.remove('show');
        alert('Network error. Please try again.');
      }
    });
  }

  /* ---------- Boot ---------- */
  document.documentElement.classList.add('js');
  document.addEventListener('DOMContentLoaded', () => {
    renderLayout();
    bindContent();
    initGlobalEvents();

    const pages = {
      home: initHome,
      products: initProducts,
      product: initProduct,
      portfolio: initPortfolio,
      contact: initContact,
      cart: initCart,
      checkout: initCheckout
    };

    const init = pages[document.body.dataset.page];
    if (init) init();
    initReveal();
  });
})();