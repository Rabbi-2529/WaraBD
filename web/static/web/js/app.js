/* =========================================================
   WaRa BD — store script (Bulletproof Checkout & Contact)
   Final version: bug fixes + empty-catalog handling + debug
   Requires: products.js (sets window.WARA_PRODUCTS)
   ========================================================= */
(function () {
  'use strict';

  /* ---------- Language ----------
     Django sets window.__WARA__.lang ("en" at "/", "bn" at "/bn/") and
     window.__WARA__.i18n = { "English text": "বাংলা" } for every string in
     this file wrapped in T() or TF() (see web/i18n_js.py + locale/bn/).
     `manage.py i18n_sync` picks those strings up automatically. */
  const WARA = window.__WARA__ || {};
  const LANG = WARA.lang || document.documentElement.lang || 'en';
  const I18N = WARA.i18n || {};
  const T = s => (I18N[s] ? I18N[s] : s);
  // TF() fills named placeholders such as %(n)s, like Django's blocktrans.
  const TF = (s, vars) => T(s).replace(/%\((\w+)\)s/g, (m, k) => (vars && vars[k] != null ? vars[k] : m));
  const BN_DIGITS = '০১২৩৪৫৬৭৮৯';
  const num = v => (LANG === 'bn' ? String(v).replace(/\d/g, d => BN_DIGITS[d]) : String(v));

  /* ---------- URLs (from Django, so Bangla pages keep their /bn/ prefix) ---------- */
  const DU = WARA.urls || {};
  const urlFrom = (p, fallback) => v => (p || fallback).replace('__slug__', encodeURIComponent(v));
  const URLS = {
    home: DU.home || '/', products: DU.products || '/products/', portfolio: DU.portfolio || '/portfolio/',
    about: DU.about || '/about/', contact: DU.contact || '/contact/', cart: DU.cart || '/cart/',
    checkout: DU.checkout || '/checkout/',
    product: urlFrom(DU.product, '/__slug__'),
    orderSuccess: urlFrom(DU.orderSuccess, '/order/success/__slug__/'),
    orderFailed: DU.orderFailed || '/order/failed/',
    apiCheckout: DU.apiCheckout || '/api/checkout/',
    apiCheckoutLookup: DU.apiCheckoutLookup || '/api/checkout/lookup/',
    apiContact: DU.apiContact || '/api/contact/'
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
  // The product ticked "Show on home page" in admin (prices, photos and Buy Now on
  // the home, about and portfolio pages). None ticked = those parts are hidden.
  const PRODUCT = CATALOG.find(p => p.featured) || FALLBACK_PRODUCT;

  const STOCK = {
    'in-stock':     { label: T('In stock'),     buy: true  },
    'out-of-stock': { label: T('Out of stock'), buy: false },
    'upcoming':     { label: T('Upcoming'),     buy: false }
  };
  const stockOf = p => STOCK[p.stock] || STOCK['in-stock'];

  /* ---------- Delivery (DB-driven with fallback) ---------- */
  const deliveryData = (window.__WARA__ && window.__WARA__.site && window.__WARA__.site.delivery) || {};
  const DELIVERY = {
    // `??` (not `||`) so a fee of 0 set in Site Settings means free delivery.
    inside:  { label: T('Inside Dhaka'),  fee: deliveryData.inside?.fee  ?? 60,  eta: deliveryData.inside?.eta  || '1-2 days' },
    outside: { label: T('Outside Dhaka'), fee: deliveryData.outside?.fee ?? 120, eta: deliveryData.outside?.eta || '2-4 days' }
  };

  const PAYMENTS = { cod: { label: T('Cash on Delivery') }, bkash: { label: T('bKash') }, nagad: { label: T('Nagad') } };
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
  const money = n => '৳' + num(Number(n).toLocaleString('en-IN'));
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
    send: '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    globe: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    /* Copied from the original storefront icon set */
    key: '<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>',
    battery: '<rect x="1" y="6" width="18" height="12" rx="2" ry="2"/><line x1="23" y1="13" x2="23" y2="11"/><line x1="5" y1="10" x2="5" y2="14"/>',
    usb: '<circle cx="12" cy="19" r="2.5"/><path d="M12 16.5V3"/><path d="M9 6l3-3 3 3"/><path d="M12 13l-4-2.5V8"/><path d="M12 11l4-2.5V6.5"/><rect x="15" y="4.5" width="2" height="2"/><circle cx="8" cy="7" r="1"/>',
    book: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    wine: '<path d="M8 22h8"/><path d="M12 15v7"/><path d="M7 2h10v6a5 5 0 0 1-10 0z"/>',
    keypad: '<circle cx="12" cy="12" r="10"/><circle cx="9" cy="8.5" r=".6"/><circle cx="12" cy="8.5" r=".6"/><circle cx="15" cy="8.5" r=".6"/><circle cx="9" cy="12" r=".6"/><circle cx="12" cy="12" r=".6"/><circle cx="15" cy="12" r=".6"/><circle cx="9" cy="15.5" r=".6"/><circle cx="12" cy="15.5" r=".6"/><circle cx="15" cy="15.5" r=".6"/>',
    eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    eyeoff: '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>',
    mobile: '<rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>',
    target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    heart: '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
    tool: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    ruler: '<path d="M21.3 8.7 8.7 21.3a1 1 0 0 1-1.4 0l-4.6-4.6a1 1 0 0 1 0-1.4L15.3 2.7a1 1 0 0 1 1.4 0l4.6 4.6a1 1 0 0 1 0 1.4z"/><path d="m7.5 10.5 2 2M10.5 7.5l2 2M13.5 4.5l2 2M4.5 13.5l2 2"/>'
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
    '<text x="300" y="420" text-anchor="middle" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#0f0f0f">' + esc(T('Image coming soon')) + '</text></svg>'
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

  /* ---------- Layout (header & footer are rendered by Django: web/partials/) ---------- */
  function renderLayout() {
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
        el.href = waLink(el.dataset.waText || T('Hi WaRa BD, I want to place an order.'));
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
    // Server-rendered images: missing or broken photos fall back to the keypad illustration.
    $$('img[data-fallback]', root).forEach(img => {
      const useFallback = () => { img.onerror = null; img.src = FALLBACK_IMG; };
      if (!img.getAttribute('src')) useFallback(); else img.onerror = useFallback;
    });
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
  // Bangla digits become English ones; letters and signs are dropped; a pasted
  // +880 / 880 prefix is removed, so the box always holds 01XXXXXXXXX.
  const cleanPhoneInput = v => {
    let s = toAsciiDigits(v).replace(/\D/g, '');
    if (/^8801/.test(s)) s = s.slice(2);  // +880 1XXX… → 01XXX…
    else if (/^881[3-9]/.test(s)) s = '0' + s.slice(2);  // +88 1XXX… → 01XXX…
    if (/^1[3-9]\d{8}$/.test(s)) s = '0' + s;  // typed without the first 0
    return s.slice(0, 11);
  };
  // What is wrong with a mobile number ('' = nothing), in words the customer understands.
  const phoneProblem = v => {
    const s = cleanPhoneInput(v);
    if (!s) return T('Enter your mobile number.');
    if (s.length >= 2 && s.slice(0, 2) !== '01') return T('Bangladeshi mobile numbers start with 01.');
    if (s.length >= 3 && !/^01[3-9]/.test(s)) return T('Mobile numbers start with 013 to 019.');
    if (s.length < 11) return TF('Enter all 11 digits (%(n)s entered).', { n: num(s.length) });
    return '';
  };
  function initPhoneInputs(root) {
    $$('input[type="tel"]', root).forEach(input => {
      input.setAttribute('inputmode', 'numeric');
      input.setAttribute('pattern', '01[3-9][0-9]{8}');
      if (!input.dataset.rule) input.dataset.rule = 'phone';
      if (input.value) input.value = cleanPhoneInput(input.value);
    });
  }

  function initGlobalEvents() {
    initPhoneInputs(document);
    document.addEventListener('keydown', e => {
      const t = e.target;
      if (!t.matches || !t.matches('input[type="tel"]') || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key && e.key.length === 1 && !/[0-9০-৯]/.test(e.key)) e.preventDefault();
    });
    document.addEventListener('input', e => {
      const t = e.target;
      if (!t.matches || !t.matches('input[type="tel"]')) return;
      const clean = cleanPhoneInput(t.value);
      if (clean !== t.value) t.value = clean;
      if (t.closest('.field.invalid')) checkField(t);
    }, true);
    document.addEventListener('focusout', e => {
      const t = e.target;
      if (!t.matches || !t.matches('input[type="tel"]') || !t.value.trim()) return;
      const clean = cleanPhoneInput(t.value);
      if (clean !== t.value) t.value = clean;
      checkField(t);
    });
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
        if (next > MAX_QTY) { toast(TF('Maximum %(n)s units per order.', { n: num(MAX_QTY) }), { type: 'error' }); return; }
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

        if (!p || !stockOf(p).buy) { toast(T('Not available.'), { type: 'error' }); return; }

        const qtyInput = scope ? $('.qty input', scope) : null;
        const qty = qtyInput ? clampQty(qtyInput.value) : 1;

        const added = Cart.add(p.id, qty);
        if (!added) { toast(T('Cart has max units.'), { type: 'error', href: URLS.cart, linkText: T('View cart') }); return; }

        toast(TF('%(n)s × %(model)s added to cart', { n: num(added), model: esc(p.model || p.name) }), { href: URLS.cart, linkText: T('View cart') });
        const label = add.innerHTML;
        add.innerHTML = icon('check') + ' ' + T('Added');
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

        if (!p || !stockOf(p).buy) { toast(T('Not available.'), { type: 'error' }); return; }

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
    }, { threshold: 0, rootMargin: '0px 0px 80px 0px' });  // show sections just before they scroll in (no blank areas)
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
      lb.innerHTML = '<button class="lb-close" aria-label="' + T('Close') + '">' + icon('x') + '</button>' +
        '<button class="gallery-nav prev" aria-label="' + T('Previous image') + '">' + icon('arrow') + '</button>' +
        '<img alt="">' +
        '<button class="gallery-nav next" aria-label="' + T('Next image') + '">' + icon('arrow') + '</button>' +
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
    $('.lb-cap', lb).textContent = num(lbIndex + 1) + ' / ' + num(n) + (lbImages[lbIndex].caption ? ' — ' + lbImages[lbIndex].caption : '');
  }
  function closeLightbox() {
    $('#lightbox').classList.remove('open');
    document.body.style.overflow = '';
  }

  /* ---------- Totals / empty helpers ---------- */
  function totalsHTML(t, deliveryText) {
    const n = { n: num(t.count) };
    const items = t.count === 1 ? TF('Subtotal (%(n)s item)', n) : TF('Subtotal (%(n)s items)', n);
    return '<div class="sum-row"><span>' + items + '</span><span>' + money(t.subtotal) + '</span></div>' +
      (t.savings > 0 ? '<div class="sum-row save"><span>' + T('You save') + '</span><span>− ' + money(t.savings) + '</span></div>' : '') +
      '<div class="sum-row"><span>' + T('Delivery') + '</span><span>' + (deliveryText || money(t.delivery)) + '</span></div>' +
      '<div class="sum-row total"><span>' + T('Total') + '</span><span>' + money(t.total) + '</span></div>';
  }
  function emptyCartHTML(title, text) {
    return '<div class="empty-state"><div class="big-icon">' + icon('cart') + '</div>' +
      '<h2>' + (title || T('Your cart is empty')) + '</h2>' +
      '<p>' + (text || T('Browse our WaRa products and add your favourites to the cart.')) + '</p>' +
      '<a class="btn btn-red" href="' + URLS.products + '">' + icon('bag') + ' ' + T('Browse products') + '</a></div>';
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
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setState(T('Locked'), false); return; }
    const code = ['2', '5', '8', '0', '#'];
    (async function loop() {
      for (;;) {
        setState(T('Locked'), false);
        await wait(1600);
        setState(T('Entering code…'), false);
        for (const k of code) {
          keyEl(k).classList.add('pressed');
          await wait(230);
          keyEl(k).classList.remove('pressed');
          await wait(170);
        }
        $$('.key', wrap).forEach(el => el.classList.add('ok'));
        setState(T('Unlocked'), true);
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
      (save ? '<span class="p-card-badge">' + TF('%(amount)s Off', { amount: money(save) }) + '</span>' : '') +
      (st.buy ? '' : '<span class="p-card-badge stock-out">' + st.label + '</span>') + '</a>' +
      '<div class="p-card-body"><span class="p-card-cat">' + esc(p.brand) + ' · ' + esc(p.category) + '</span>' +
      '<h3><a href="' + productUrl(p) + '">' + esc(p.name) + '</a></h3>' +
      '<div class="p-card-price"><strong>' + money(p.price) + '</strong>' + (save ? '<s>' + money(p.oldPrice) + '</s>' : '') + '</div>' +
      '<div class="p-card-actions">' +
      (st.buy
        ? '<button type="button" class="btn btn-green" data-add-to-cart>' + icon('cart') + ' ' + T('Add to Cart') + '</button>' +
          '<button type="button" class="btn btn-red" data-buy-now>' + T('Buy Now') + '</button>'
        : '<a class="btn btn-outline" href="' + productUrl(p) + '">' + T('View details') + '</a>') +
      '</div></div></article>';
  }

  function comingSoonHTML() {
    if (CATALOG.length >= 4) return '';
    return '<div class="p-card soon"><div class="icon-box green">' + icon('box') + '</div>' +
      '<h3>' + T('More WaRa products coming soon') + '</h3>' +
      '<p>' + T('New smart security products are on the way. Message us to hear first when they arrive.') + '</p>' +
      '<a class="link-arrow" target="_blank" rel="noopener" href="' + waLink(T('Hi WaRa BD, please let me know when new products arrive.')) + '">' + T('Get notified') + ' ' + icon('arrow') + '</a></div>';
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
        '<h2>' + T('No products yet') + '</h2><p>' + T('Products added in the admin panel will appear here.') + '</p></div>';
      return;
    }

    const prices = CATALOG.map(p => p.price);
    const floor = prices.length ? Math.floor(Math.min.apply(null, prices) / 500) * 500 : 0;
    let ceil = prices.length ? Math.ceil(Math.max.apply(null, prices) / 500) * 500 : 1000;
    if (ceil <= floor) ceil = floor + 500;
    if (minR) [minR, maxR, minN, maxN].forEach(el => { el.min = floor; el.max = ceil; el.step = 50; });

    const optHTML = (group, value, label, n) => '<label class="filter-opt"><span><input type="checkbox" name="' + group + '" value="' + esc(value) + '"> ' + esc(label) + '</span><span class="count">' + num(n) + '</span></label>';
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
      const counts = { shown: '<b>' + num(list.length) + '</b>', total: '<b>' + num(CATALOG.length) + '</b>' };
      if ($('#shopCount')) $('#shopCount').innerHTML = CATALOG.length === 1
        ? TF('Showing %(shown)s of %(total)s product', counts)
        : TF('Showing %(shown)s of %(total)s products', counts);
      if (!list.length) {
        grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="big-icon">' + icon('zoom') + '</div><h2>' + T('No products match your filters') + '</h2><p>' + T('Try a wider price range or clear the filters.') + '</p><button type="button" class="btn btn-red" data-reset-filters>' + T('Reset filters') + '</button></div>';
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
  /* ---------- Product page ----------
     The page is rendered by Django (web/templates/web/product.html);
     this only adds behaviour: gallery, lightbox, tabs, sticky buy bar. */
  function initProduct() {
    let images = [];
    try {
      const data = $('#product-images');
      images = data ? JSON.parse(data.textContent) : [];
    } catch (e) { images = []; }
    if (!Array.isArray(images) || !images.length) images = [{ src: FALLBACK_IMG, caption: '' }];

    // Gallery + lightbox
    const main = $('#gMain');
    const thumbs = $('#gThumbs');
    let current = 0;
    const show = i => {
      current = (i + images.length) % images.length;
      const img = $('#gMainImg');
      if (img) {
        img.src = images[current].src;
        if (images[current].caption) img.alt = images[current].caption;
      }
      if (thumbs) $$('button', thumbs).forEach((b, bi) => b.classList.toggle('active', bi === current));
    };
    if (thumbs) {
      thumbs.addEventListener('click', e => {
        const b = e.target.closest('button');
        if (b) show(+b.dataset.i);
      });
    }
    if (main) main.addEventListener('click', () => openLightbox(images, current));

    // Tabs — also opened by #specs, #faq, #warranty … links (e.g. from the footer).
    const tabBtns = $$('#productTabs .tab-list button');
    const activate = (name, focus) => {
      tabBtns.forEach(b => {
        const on = b.dataset.tab === name;
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', String(on));
        b.tabIndex = on ? 0 : -1;
        const panel = $('#tab-' + b.dataset.tab);
        if (panel) panel.classList.toggle('active', on);
        if (on && focus) b.focus();
      });
    };
    tabBtns.forEach((b, i) => {
      b.tabIndex = b.classList.contains('active') ? 0 : -1;
      b.addEventListener('click', () => activate(b.dataset.tab));
      b.addEventListener('keydown', e => {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        const step = e.key === 'ArrowRight' ? 1 : -1;
        const next = tabBtns[(i + step + tabBtns.length) % tabBtns.length];
        activate(next.dataset.tab, true);
      });
    });
    const openFromHash = () => {
      const hash = location.hash.replace('#', '');
      if (!hash || !tabBtns.some(b => b.dataset.tab === hash)) return;
      activate(hash);
      const tabs = $('#productTabs');
      if (tabs) tabs.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    openFromHash();
    window.addEventListener('hashchange', openFromHash);

    // Mobile sticky buy bar: visible once the main buy buttons scroll off the top.
    const sticky = $('#stickyBuy');
    const buyRow = $('#buyRow');
    if (sticky && buyRow) {
      const onScroll = () => sticky.classList.toggle('show', buyRow.getBoundingClientRect().bottom < 0);
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    }
  }

  /* ---------- Portfolio ---------- */
  const USE_CASES = (window.__WARA__ && Array.isArray(window.__WARA__.useCases)) ? window.__WARA__.useCases : [];
  const CATS = { all: T('All'), home: T('Home'), office: T('Office'), hospitality: T('Hospitality & Health'), public: T('Public Spaces'), commercial: T('Commercial') };

  function initPortfolio() {
    // No use cases entered yet: hide that section instead of showing an empty grid.
    const ucGrid = $('#pfGrid');
    if (ucGrid && !USE_CASES.length) ucGrid.closest('section').hidden = true;
    const pg = $('#photoGrid');
    if (!pg) return;
    pg.innerHTML = PRODUCT.images.map((im, i) =>
      '<figure data-i="' + i + '" tabindex="0" role="button" aria-label="' + T('Enlarge') + ': ' + esc(im.caption) + '">' +
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
      '<article class="pf-card" data-cat="' + u.cat + '"><div class="pf-visual ' + u.tone + '"><span class="pf-cat">' + CATS[u.cat] + '</span>' + icon(u.icon, 'big') + '</div><div class="pf-body"><h3>' + esc(u.title) + '</h3><p>' + esc(u.text) + '</p><span class="pf-mode' + (u.mode === 'public' ? ' red' : '') + '">' + icon(u.mode === 'public' ? 'users' : 'user') + (u.mode === 'public' ? T('Public (visitor) mode') : T('Private mode')) + (u.place ? ' · ' + esc(u.place) : '') + '</span></div></article>'
    ).join('');

    if (pF) pF.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) return;
      $$('#pfFilters button').forEach(x => x.classList.toggle('active', x === b));
      $$('#pfGrid .pf-card').forEach(c => c.classList.toggle('hide', b.dataset.f !== 'all' && c.dataset.cat !== b.dataset.f));
    });
  }

  /* ---------- Contact ---------- */
  const toAsciiDigits = v => String(v).replace(/[০-৯]/g, d => String(BN_DIGITS.indexOf(d)));
  const DRAFT_KEY = 'wara_checkout_draft';
  const RULES = {
    name: v => v.trim().length >= 3 || T('Please enter your full name.'),
    // Bangla digits typed on a Bangla keyboard are accepted and converted.
    phone: v => phoneProblem(v) || true,
    email: v => !v.trim() || /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) || T('Enter a valid email address.'),
    address: v => v.trim().length >= 10 || T('Please enter your full address.'),
    required: v => v.trim().length > 0 || T('This field is required.'),
    choice: v => v.trim().length > 0 || T('Please select an option.'),
    message: v => v.trim().length >= 10 || T('Please write at least 10 characters.'),
    trx: v => /^[A-Za-z0-9]{6,}$/.test(v.trim()) || T('Enter the transaction ID from your payment SMS.')
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
  // Show field errors returned by the server ({ errors: { phone: '...' } }).
  function showServerErrors(form, errors) {
    let first = null;
    Object.keys(errors || {}).forEach(name => {
      const input = form.elements[name];
      const el = input && input.length !== undefined && !input.tagName ? input[0] : input;
      const wrap = el && el.closest ? el.closest('.field') : null;
      if (!wrap) return;
      wrap.classList.add('invalid');
      el.setAttribute('aria-invalid', 'true');
      let err = $('.err', wrap);
      if (!err) { err = document.createElement('div'); err.className = 'err'; wrap.appendChild(err); }
      err.textContent = errors[name];
      if (!first) first = el;
    });
    if (first) first.focus();
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
      if (bad) { bad.focus(); toast(T('Please fix the highlighted fields.'), { type: 'error' }); return; }

      const data = Object.fromEntries(new FormData(form).entries());

      const btn = form.querySelector('button[type="submit"]');
      const originalText = btn.innerHTML;
      btn.innerHTML = T('Sending…');
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
          showServerErrors(form, result.errors);
          toast(result.error || T('Could not send your message.'), { type: 'error' });
          btn.innerHTML = originalText;
          btn.disabled = false;
        }
      } catch (err) {
        toast(T('Network error. Please try again.'), { type: 'error' });
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
        btn.innerHTML = '<i data-icon="send"></i> ' + T('Send message');
        btn.disabled = false;
      }
      bindContent(form);
    });
  }

  /* ---------- Cart lines (cart page + side cart) ---------- */
  const lowestFee = () => Math.min(DELIVERY.inside.fee, DELIVERY.outside.fee);
  function cartLineHTML(l) {
    const p = l.product;
    const meta = [p.model ? T('Model') + ': ' + esc(p.model) : '', p.color ? T('Color') + ': ' + esc(p.color) : ''].filter(Boolean);
    return '<article class="ci" data-id="' + esc(l.id) + '">' +
      '<a class="ci-img" href="' + productUrl(p) + '">' + productImg(p) + '</a>' +
      '<div class="ci-info">' +
        '<h3><a href="' + productUrl(p) + '">' + esc(p.name) + '</a></h3>' +
        (meta.length ? '<p class="ci-meta">' + meta.map(m => '<span>' + m + '</span>').join('') + '</p>' : '') +
        '<p class="ci-price"><strong>' + money(p.price) + '</strong>' + (p.oldPrice ? ' <del>' + money(p.oldPrice) + '</del>' : '') + '</p>' +
      '</div>' +
      '<div class="ci-qty">' + qtyHTML(l.qty, 'sm') + '</div>' +
      '<div class="ci-total"><span>' + T('Total') + '</span><strong data-line-total>' + money(l.total) + '</strong></div>' +
      '<button type="button" class="ci-remove" data-remove="' + esc(l.id) + '" aria-label="' + T('Remove') + '" title="' + T('Remove') + '">' + icon('trash') + '</button>' +
    '</article>';
  }
  function bindCartLines(root) {
    root.addEventListener('change', e => {
      const row = e.target.closest('[data-id]');
      if (row && e.target.matches('.qty input')) Cart.setQty(row.dataset.id, e.target.value);
    });
    root.addEventListener('click', e => {
      const rm = e.target.closest('[data-remove]');
      if (rm) {
        const snapshot = Cart.items();
        Cart.remove(rm.dataset.remove);
        toast(T('Item removed from cart'), { actionText: T('Undo'), onAction: () => Cart.restore(snapshot) });
      }
      if (e.target.closest('[data-clear-cart]')) {
        const snapshot = Cart.items();
        Cart.clear();
        toast(T('Cart cleared'), { actionText: T('Undo'), onAction: () => Cart.restore(snapshot) });
      }
    });
  }
  // Quantity boxes keep their focus while typing: only the numbers around them are repainted.
  function repaintCartLines(root, t) {
    const rows = $$('[data-id]', root);
    if (rows.length !== t.lines.length) return false;
    for (const l of t.lines) {
      const row = $('[data-id="' + l.id + '"]', root);
      if (!row) return false;
      $('[data-line-total]', row).textContent = money(l.total);
      const input = $('.qty input', row);
      if (+input.value !== l.qty) { input.value = l.qty; syncQty($('.qty', row)); }
    }
    return true;
  }

  /* ---------- Cart page ---------- */
  function initCart() {
    const mount = $('#cartMount');
    if (!mount) return;
    const summaryHTML = t => '<h3>' + T('Order summary') + '</h3>' + totalsHTML(t, T('At checkout')) +
      '<a class="btn btn-red btn-block cart-go" href="' + URLS.checkout + '">' + icon('lock') + ' ' + T('Proceed to checkout') + '</a>' +
      '<p class="summary-note">' + icon('truck') + TF('Delivery from %(fee)s · Cash on delivery', { fee: money(lowestFee()) }) + '</p>' +
      '<div class="pay-chips" aria-label="' + T('Payment method') + '"><span>' + icon('cash') + ' ' + T('Cash on Delivery') + '</span><span class="bk">' + T('bKash') + '</span><span class="ng">' + T('Nagad') + '</span></div>';
    const countText = n => n === 1 ? TF('%(n)s item', { n: num(n) }) : TF('%(n)s items', { n: num(n) });
    const render = () => {
      const t = Cart.totals();
      if (!t.lines.length) { mount.innerHTML = emptyCartHTML(); return; }
      mount.innerHTML =
        '<div class="cart-layout"><div class="cart-card">' +
          '<div class="cart-card-head"><h2>' + icon('cart') + ' ' + T('Your cart') + ' <span data-cart-count>' + countText(t.count) + '</span></h2>' +
          '<button type="button" class="link-btn" data-clear-cart>' + icon('trash') + ' ' + T('Clear cart') + '</button></div>' +
          '<div class="ci-list">' + t.lines.map(cartLineHTML).join('') + '</div>' +
          '<div class="cart-card-foot"><a class="btn btn-outline btn-sm" href="' + URLS.products + '">' + icon('back') + ' ' + T('Continue shopping') + '</a>' +
          (t.savings > 0 ? '<span class="cart-saving">' + icon('award') + ' ' + TF('You save %(amount)s on this order', { amount: money(t.savings) }) + '</span>' : '') +
          '</div>' +
        '</div>' +
        '<aside class="summary cart-summary" id="cartSummary">' + summaryHTML(t) + '</aside></div>';
    };
    const update = () => {
      const t = Cart.totals();
      if (!t.lines.length || !repaintCartLines(mount, t)) { render(); return; }
      const count = $('[data-cart-count]', mount);
      if (count) count.textContent = countText(t.count);
      const summary = $('#cartSummary');
      if (summary) summary.innerHTML = summaryHTML(t);
    };
    bindCartLines(mount);
    document.addEventListener('cart:change', update);
    render();
  }

  /* ---------- Side cart (opens from the header cart button and after "Add to cart") ---------- */
  function initMiniCart() {
    const page = document.body.dataset.page;
    if (page === 'cart' || page === 'checkout') return;  // those pages already show the cart
    const root = document.createElement('div');
    root.className = 'mini-cart';
    root.hidden = true;
    root.innerHTML =
      '<div class="mc-backdrop" data-mc-close></div>' +
      '<aside class="mc-panel" role="dialog" aria-modal="true" aria-labelledby="mcTitle" tabindex="-1">' +
        '<header class="mc-head"><div class="mc-brand"></div>' +
        '<button type="button" class="mc-close" data-mc-close aria-label="' + T('Close') + '">' + icon('x') + '</button>' +
        '<h2 id="mcTitle">' + icon('cart') + ' ' + T('Your cart') + ' <span class="mc-count"></span></h2></header>' +
        '<div class="mc-body"></div>' +
        '<footer class="mc-foot"></footer>' +
      '</aside>';
    document.body.appendChild(root);
    // The shop's logo (uploaded logo or the WaRa BD text logo) at the top of the side cart.
    const siteLogo = $('.site-header .logo');
    if (siteLogo) {
      const logo = siteLogo.cloneNode(true);
      logo.removeAttribute('id');
      $('.mc-brand', root).appendChild(logo);
    }
    // Floating cart button on the right side of every page (opens this side cart).
    const floatBtn = document.createElement('button');
    floatBtn.type = 'button';
    floatBtn.className = 'cart-float';
    floatBtn.setAttribute('aria-label', T('Shopping cart'));
    floatBtn.innerHTML = icon('cart') + '<span class="cf-label">' + T('Cart') + '</span><span class="cart-count">' + num(Cart.count()) + '</span>';
    document.body.appendChild(floatBtn);
    floatBtn.addEventListener('click', () => open());
    const panel = $('.mc-panel', root), body = $('.mc-body', root), foot = $('.mc-foot', root), count = $('.mc-count', root);
    let lastFocus = null;

    const render = () => {
      const t = Cart.totals();
      count.textContent = t.count ? '· ' + (t.count === 1 ? TF('%(n)s item', { n: num(t.count) }) : TF('%(n)s items', { n: num(t.count) })) : '';
      if (!t.lines.length) {
        body.innerHTML = '<div class="mc-empty"><div class="big-icon">' + icon('cart') + '</div><h3>' + T('Your cart is empty') + '</h3>' +
          '<p>' + T('Browse our WaRa products and add your favourites to the cart.') + '</p>' +
          '<a class="btn btn-red btn-sm" href="' + URLS.products + '">' + icon('bag') + ' ' + T('Browse products') + '</a></div>';
        foot.innerHTML = '';
        return;
      }
      if (!repaintCartLines(body, t)) body.innerHTML = '<div class="ci-list">' + t.lines.map(cartLineHTML).join('') + '</div>';
      foot.innerHTML =
        '<div class="mc-sum"><span>' + T('Subtotal') + '</span><strong>' + money(t.subtotal) + '</strong></div>' +
        (t.savings > 0 ? '<div class="mc-sum save"><span>' + T('You save') + '</span><span>− ' + money(t.savings) + '</span></div>' : '') +
        '<p class="mc-note">' + icon('truck') + ' ' + T('Delivery charge is added at checkout, by your district.') + '</p>' +
        '<div class="mc-actions"><a class="btn btn-outline" href="' + URLS.cart + '">' + T('View cart') + '</a>' +
        '<a class="btn btn-red" href="' + URLS.checkout + '">' + T('Checkout') + ' ' + icon('arrow') + '</a></div>';
    };
    const open = () => {
      render();
      lastFocus = document.activeElement;
      root.hidden = false;
      document.body.classList.add('mc-lock');
      requestAnimationFrame(() => { root.classList.add('open'); panel.focus(); });
    };
    const close = () => {
      if (root.hidden) return;
      root.classList.remove('open');
      document.body.classList.remove('mc-lock');
      setTimeout(() => { root.hidden = true; }, 280);
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    };

    document.addEventListener('click', e => {
      const btn = e.target.closest('a.cart-btn:not(.account-btn)');
      if (btn && !e.ctrlKey && !e.metaKey && !e.shiftKey) { e.preventDefault(); open(); }
    });
    root.addEventListener('click', e => { if (e.target.closest('[data-mc-close]')) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
    bindCartLines(body);
    document.addEventListener('cart:change', () => { if (!root.hidden) render(); });
  }

  /* ---------- District → thana dropdowns (Select2) ----------
     Data comes from Django (<script id="wara-locations">): districts with
     their delivery charge and thanas (a thana may have its own charge).
     Values stay in English (what the server stores); labels follow the page language. */
  function bindLocationSelects(root, opts) {
    opts = opts || {};
    const dEl = $('[data-district-select]', root);
    const tEl = $('[data-thana-select]', root);
    const dataEl = $('#wara-locations');
    if (!dEl || !tEl || !dataEl) return null;
    let data = [];
    try { data = JSON.parse(dataEl.textContent) || []; } catch (e) { data = []; }
    const byName = {};
    data.forEach(d => { byName[d.v] = d; });
    const $j = window.jQuery && window.jQuery.fn && window.jQuery.fn.select2 ? window.jQuery : null;
    const onChange = typeof opts.onChange === 'function' ? opts.onChange : () => {};

    const option = (value, label) => '<option value="' + esc(value) + '">' + esc(label) + '</option>';
    dEl.innerHTML = option('', T('Select your district')) + data.map(d => option(d.v, d.l)).join('');

    const fillThanas = (selected) => {
      const d = byName[dEl.value];
      const list = d ? d.t : [];
      tEl.innerHTML = option('', d ? T('Select thana / upazila') : T('Select district first')) +
        list.map(t => option(t[0], t[1])).join('');
      if (selected) {
        if (!list.some(t => t[0] === selected)) tEl.insertAdjacentHTML('beforeend', option(selected, selected));
        tEl.value = selected;
      }
      tEl.disabled = !d;
    };

    const district = () => byName[dEl.value] || null;
    const thanaRow = () => {
      const d = district();
      return d ? d.t.find(t => t[0] === tEl.value) || null : null;
    };
    const api = {
      district,
      fee: () => {
        const d = district();
        if (!d) return null;
        const t = thanaRow();
        return t && t[2] != null ? t[2] : d.f;
      },
      placeLabel: () => {
        const d = district();
        const t = thanaRow();
        return t ? t[1] + ', ' + d.l : (tEl.value && d ? tEl.value + ', ' + d.l : (d ? d.l : ''));
      }
    };

    dEl.value = opts.district || dEl.dataset.selected || '';
    fillThanas(opts.thana || tEl.dataset.selected || '');

    const changed = (which) => () => {
      if (which === 'district') { fillThanas(''); if ($j) $j(tEl).trigger('change.select2'); }
      const wrap = (which === 'district' ? dEl : tEl).closest('.field');
      if (wrap && wrap.classList.contains('invalid')) checkField(which === 'district' ? dEl : tEl);
      onChange();
    };

    if ($j) {
      const language = {
        noResults: () => T('No results found'),
        searching: () => T('Searching…')
      };
      const common = { width: '100%', language };
      $j(dEl).select2(Object.assign({ placeholder: T('Select your district') }, common));
      $j(tEl).select2(Object.assign({
        placeholder: T('Select thana / upazila'),
        tags: true,  // a thana missing from the list can be typed
        createTag: p => { const term = p.term.trim(); return term ? { id: term, text: term + ' (' + T('type your own') + ')', newTag: true } : null; }
      }, common));
      $j(dEl).on('change', changed('district'));
      $j(tEl).on('change', changed('thana'));
    } else {
      dEl.addEventListener('change', changed('district'));
      tEl.addEventListener('change', changed('thana'));
    }
    // Fill in a district + thana (e.g. from the customer's last order).
    api.set = (district, thana) => {
      const d = byName[district] || data.find(x => x.v.toLowerCase() === String(district || '').toLowerCase());
      if (!d) return false;
      dEl.value = d.v;
      if ($j) $j(dEl).trigger('change.select2');
      fillThanas(thana || '');
      if ($j) $j(tEl).trigger('change.select2');
      [dEl, tEl].forEach(el => { const w = el.closest('.field'); if (w && w.classList.contains('invalid')) checkField(el); });
      onChange();
      return true;
    };
    return api;
  }

  function initAccount() {
    // My Account → address form: same district → thana dropdowns.
    const form = $('form[data-address-form]');
    if (form) bindLocationSelects(form);
  }

  /* ---------- Checkout ---------- */
  function initCheckout() {
    const mount = $('#checkoutMount');
    const form = $('#checkoutForm');
    if (!mount || !form) return;

    if (!Cart.count()) {
      mount.innerHTML = emptyCartHTML(T('Nothing to check out yet'), T('Your cart is empty. Add a product first.'));
      return;
    }

    // District → thana dropdowns (Select2). The delivery charge is never chosen
    // by the customer: it follows the district / thana (server checks it again).
    const draft = store.get(DRAFT_KEY, null);
    const loc = bindLocationSelects(form, {
      district: (draft && draft.district) || undefined,
      thana: (draft && draft.thana) || undefined,
      onChange: () => { paintSummary(); paintPayment(); paintQuote(); }
    });

    // Form values saved before going to the SMS code page come back here
    // (e.g. after "Change number"), so nothing has to be typed twice.
    if (draft && typeof draft === 'object') {
      ['name', 'phone', 'email', 'address', 'note', 'sender', 'trx'].forEach(k => {
        if (draft[k] != null && form.elements[k]) form.elements[k].value = draft[k];
      });
      const radio = draft.payment && form.querySelector('input[name="payment"][value="' + draft.payment + '"]');
      if (radio) radio.checked = true;
    }
    if (params.get('change') === 'phone' && form.elements.phone) {
      form.elements.phone.focus();
      form.elements.phone.select();
    }

    /* Mobile number first: a returning customer's details are filled in.
       From this browser's own earlier orders, or (logged in / number confirmed
       by SMS today) from the server. Fields already typed are never overwritten. */
    const PROFILES_KEY = 'wara_checkout_profiles';
    const phoneEl = form.elements.phone;
    const found = $('#coFound');
    const cleanPhone = cleanPhoneInput;
    const fillDetails = d => {
      if (!d) return false;
      let filled = false;
      [['name', d.name], ['email', d.email], ['address', d.address]].forEach(([k, v]) => {
        const el = form.elements[k];
        if (el && v && !el.value.trim()) { el.value = v; filled = true; }
      });
      if (d.district && loc && !form.elements.district.value) filled = loc.set(d.district, d.thana) || filled;
      if (filled && found) found.hidden = false;
      return filled;
    };
    let lookedUp = '';
    const onPhone = () => {
      const p = cleanPhone(phoneEl.value);
      if (found) found.hidden = true;
      if (!/^01[3-9]\d{8}$/.test(p) || p === lookedUp) return;
      lookedUp = p;
      const saved = (store.get(PROFILES_KEY, {}) || {})[p];
      if (fillDetails(saved)) return;
      const csrf = form.querySelector('[name="csrfmiddlewaretoken"]');
      fetch(URLS.apiCheckoutLookup, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf ? csrf.value : '' },
        body: JSON.stringify({ phone: p })
      }).then(r => r.json()).then(d => { if (d && d.found && cleanPhone(phoneEl.value) === p) fillDetails(d); }).catch(() => {});
    };
    const rememberDetails = payload => {
      const p = cleanPhone(payload.phone);
      if (!p) return;
      const all = store.get(PROFILES_KEY, {}) || {};
      delete all[p];
      all[p] = { name: payload.name, email: payload.email, district: payload.district, thana: payload.thana, address: payload.address };
      const keys = Object.keys(all);
      keys.slice(0, Math.max(0, keys.length - 3)).forEach(k => delete all[k]);  // keep the last 3 numbers
      store.set(PROFILES_KEY, all);
    };
    if (phoneEl) phoneEl.addEventListener('input', onPhone);

    const summaryMount = $('#coSummary');
    const pay = () => {
      const el = form.elements.payment;
      if (!el) return 'cod';
      const v = el.value;
      return v && PAYMENTS[v] ? v : 'cod';
    };
    const deliveryFee = () => (loc ? loc.fee() : null);  // null until a district is chosen
    const orderTotal = () => Cart.totals().subtotal + (deliveryFee() || 0);

    const paintQuote = () => {
      const box = $('#deliveryQuote');
      if (!box || !loc) return;
      const d = loc.district();
      $('[data-quote-text]', box).innerHTML = d
        ? TF('Delivery charge to %(place)s: %(fee)s', { place: '<strong>' + esc(loc.placeLabel()) + '</strong>', fee: '<strong>' + money(loc.fee()) + '</strong>' }) +
          (d.e ? ' · ' + esc(d.e) : '')
        : esc(T('Choose your district to see the delivery charge.'));
      box.classList.toggle('ready', !!d);
    };

    const paintSummary = () => {
      if (!summaryMount) return;
      const t = Cart.totals();
      const fee = deliveryFee();
      // Each line: picture, name, unit price, quantity box, line total and a remove button.
      summaryMount.innerHTML = '<h3>' + T('Your order') + '</h3>' +
        (t.lines.length ? '' : '<div class="sum-empty">' + icon('cart') + '<p>' + T('Your cart is empty. Add a product first.') + '</p>' +
          '<a class="btn btn-outline btn-sm" href="' + URLS.products + '">' + icon('bag') + ' ' + T('Browse products') + '</a></div>') +
        t.lines.map(l => '<div class="sum-item" data-id="' + esc(l.id) + '"><a class="sum-img" href="' + productUrl(l.product) + '">' + productImg(l.product) + '</a>' +
          '<div class="meta"><h4>' + esc(l.product.name) + '</h4><span class="sum-price"><strong>' + money(l.product.price) + '</strong>' +
          (l.product.oldPrice ? ' <del>' + money(l.product.oldPrice) + '</del>' : '') + '</span></div>' +
          '<div class="sum-qty">' + qtyHTML(l.qty, 'sm') + '</div>' +
          '<div class="sum-side"><div class="price">' + money(l.total) + '</div>' +
          '<button type="button" class="sum-remove" data-remove="' + esc(l.id) + '" aria-label="' + T('Remove') + '" title="' + T('Remove') + '">' + icon('trash') + '</button></div></div>').join('') +
        (t.lines.length ? '<div class="sum-row"><span>' + T('Subtotal') + '</span><span>' + money(t.subtotal) + '</span></div>' +
        '<div class="sum-row"><span>' + T('Delivery') + (loc && loc.district() ? ' (' + esc(loc.placeLabel()) + ')' : '') + '</span><span>' +
          (fee == null ? T('Select district') : money(fee)) + '</span></div>' +
        '<div class="sum-row total"><span>' + T('Total') + '</span><span>' + money(orderTotal()) + '</span></div>' : '') +
        '<button type="submit" class="btn btn-red btn-block mt-3" id="placeOrder"' + (t.lines.length ? '' : ' disabled') + '>' +
          icon('lock') + ' ' + T('Place order') + (t.lines.length ? ' · ' + money(orderTotal()) : '') + '</button>';
    };

    // bKash / Nagad: show the "Send Money" steps, amount, merchant number
    // and the sender number + TrxID fields only when one is selected.
    const mobilePay = $('#mobilePay');
    const paintPayment = () => {
      if (!mobilePay) return;
      const p = pay();
      const isMobile = p === 'bkash' || p === 'nagad';
      mobilePay.classList.toggle('show', isMobile);
      if (!isMobile) return;
      $$('.pay-name', mobilePay).forEach(el => { el.textContent = PAYMENTS[p].label; });
      $$('.pay-amount', mobilePay).forEach(el => { el.textContent = money(orderTotal()); });
      const merchant = $('#payMerchant');
      if (merchant) merchant.textContent = (SITE.merchant && SITE.merchant[p]) || '';
    };

    paintSummary();
    paintPayment();
    paintQuote();
    liveValidate(form);
    // A number already in the box (logged-in customer, saved draft): look it up only now,
    // after the summary is drawn — filling the district repaints it.
    if (phoneEl && phoneEl.value) onPhone();

    $$('input[name="payment"]', form).forEach(r => r.addEventListener('change', paintPayment));
    // Change quantities or remove products right in "Your order".
    if (summaryMount) {
      summaryMount.addEventListener('change', e => {
        const row = e.target.closest('.sum-item');
        if (row && e.target.matches('.qty input')) Cart.setQty(row.dataset.id, e.target.value);
      });
      summaryMount.addEventListener('click', e => {
        const rm = e.target.closest('[data-remove]');
        if (!rm) return;
        const snapshot = Cart.items();
        Cart.remove(rm.dataset.remove);
        toast(T('Item removed from cart'), { actionText: T('Undo'), onAction: () => Cart.restore(snapshot) });
      });
      document.addEventListener('cart:change', () => { paintSummary(); paintPayment(); });
    }
    const termsInput = form.elements.terms;
    if (termsInput) termsInput.addEventListener('change', () => { if (termsInput.checked) $('#coTerms').classList.remove('invalid'); });

    form.addEventListener('submit', async e => {
      e.preventDefault();
      if (!Cart.count()) { toast(T('Your cart is empty. Add a product first.'), { type: 'error' }); return; }

      const bad = validateForm(form);
      const terms = form.elements.terms;
      const termsBox = $('#coTerms');
      const termsOk = !!(terms && terms.checked);
      if (termsBox) termsBox.classList.toggle('invalid', !termsOk);
      if (bad) { bad.focus(); toast(T('Please fix the highlighted fields.'), { type: 'error' }); return; }
      if (!termsOk) {
        if (termsBox) {
          termsBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
          termsBox.classList.remove('shake'); void termsBox.offsetWidth; termsBox.classList.add('shake');
        }
        toast(T('Please confirm your details and accept the delivery & warranty policy.'), { type: 'error' });
        return;
      }

      const csrfInput = form.querySelector('[name="csrfmiddlewaretoken"]');
      const csrfToken = csrfInput ? csrfInput.value : '';
      const isMobile = pay() === 'bkash' || pay() === 'nagad';

      const payload = {
        name: form.elements.name.value.trim(),
        phone: toAsciiDigits(form.elements.phone.value.trim()),
        email: form.elements.email.value.trim(),
        district: form.elements.district.value,
        address: form.elements.address.value.trim(),
        note: form.elements.note ? form.elements.note.value.trim() : '',
        payment: pay(),
        sender: isMobile && form.elements.sender ? toAsciiDigits(form.elements.sender.value.trim()) : '',
        trx: isMobile && form.elements.trx ? form.elements.trx.value.trim().toUpperCase() : '',
        thana: form.elements.thana ? form.elements.thana.value : '',
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
          rememberDetails(payload);
          Cart.clear();
          store.remove(DRAFT_KEY);
          location.href = URLS.orderSuccess(result.order_number);
        } else if (result.otp_required && result.redirect) {
          // Guest: confirm the mobile number with an SMS code; the order is
          // placed on the code page. Keep the form in case they change number.
          store.set(DRAFT_KEY, Object.assign({}, payload, { lines: undefined }));
          rememberDetails(payload);
          location.href = result.redirect;
        } else {
          if (proc) proc.classList.remove('show');
          showServerErrors(form, result.errors);
          toast(result.error || T('Could not place your order. Please try again.'), { type: 'error' });
        }
      } catch (err) {
        if (proc) proc.classList.remove('show');
        toast(T('Network error. Please try again.'), { type: 'error' });
      }
    });
  }

  /* ---------- Order placed: empty the cart and the saved checkout form ---------- */
  function initSuccess() {
    Cart.clear();
    store.remove(DRAFT_KEY);
  }

  /* ---------- SMS code page ---------- */
  function initOtp() {
    const input = $('.otp-input');
    if (input) {
      // Submit as soon as 6 digits (English or Bangla) are typed or pasted.
      input.addEventListener('input', () => {
        const digits = toAsciiDigits(input.value).replace(/\D/g, '');
        if (digits.length === 6 && input.form) { input.value = digits; input.form.requestSubmit(); }
      });
    }
    const resend = $('#otpResend');
    if (!resend) return;
    const label = $('span', resend);
    let wait = parseInt(resend.dataset.wait, 10) || 0;
    const clock = s => Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
    const tick = () => {
      if (wait > 0) {
        resend.disabled = true;
        label.textContent = label.dataset.waitLabel.replace('%(s)s', num(clock(wait)));
        wait -= 1;
        setTimeout(tick, 1000);
      } else {
        resend.disabled = false;
        label.textContent = label.dataset.label;
      }
    };
    tick();
  }

  /* ---------- Boot ---------- */
  document.documentElement.classList.add('js');
  document.addEventListener('DOMContentLoaded', () => {
    renderLayout();
    bindContent();
    initGlobalEvents();
    initMiniCart();

    const pages = {
      home: initHome,
      products: initProducts,
      product: initProduct,
      portfolio: initPortfolio,
      contact: initContact,
      cart: initCart,
      checkout: initCheckout,
      success: initSuccess,
      otp: initOtp,
      account: initAccount
    };

    const init = pages[document.body.dataset.page];
    if (init) init();
    initReveal();
  });
})();