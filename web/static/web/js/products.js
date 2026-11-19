/* =========================================================
   WaRa BD — product catalog (Django Bridge)
   File: static/web/js/products.js

   Reads products from Django's window.__WARA__.products,
   exposes them as window.WARA_PRODUCTS for the storefront.

   Load this BEFORE app.js in your template.
   ========================================================= */
window.WARA_PRODUCTS = (function () {
  'use strict';

  const source =
    window.__WARA__ &&
    window.__WARA__.products;

  const isValid = function (p) {
    return (
      p !== null &&
      typeof p === 'object' &&
      !Array.isArray(p) &&
      p.id != null &&
      String(p.id).length > 0 &&
      typeof p.name === 'string' &&
      p.name.length > 0
    );
  };

  if (Array.isArray(source)) {
    const valid = source.filter(isValid);
    if (valid.length) {
      window.__WARA_PRODUCTS_SOURCE = 'django';
      return valid;
    }
  }

  /* ---- Fallback: hardcoded catalog (only used when Django sends nothing usable) ---- */
  window.__WARA_PRODUCTS_SOURCE = 'fallback';

  const IMG = 'https://admin.felnatech.com/storage/app/public/products/';

  return [
    {
      id: 'ft-scl029',
      featured: true,
      brand: 'WaRa',
      category: 'Smart Cabinet Lock',
      name: 'WaRa FT-SCL029 Cabinet Drawer Lock',
      subtitle: 'With Visitor Password Changing Access',
      model: 'FT-SCL029',
      sku: 'WR-SCL029-BK',
      color: 'Black',
      price: 1975,
      oldPrice: 2050,
      stock: 'in-stock',
      warranty: '1 Year',
      added: '2026-10-22',
      short: 'A compact round keypad and a motorized lock body that turn any cabinet, drawer, wardrobe or locker into keyless, code-protected storage.',
      images: [
        { src: IMG + 'ft-scl029-felnatech-6609-ft.jpg', caption: 'Round keypad & motorized lock body' },
        { src: IMG + 'ft-scl029-felnatech-6609-1.jpg',  caption: 'Compact keypad — fits in your palm' },
        { src: IMG + 'ft-scl029-felnatech-6609-2.jpg',  caption: 'Front-mounted keypad on a cabinet door' },
        { src: IMG + 'ft-scl029-felnatech-6609-3.jpg',  caption: 'Installed on wardrobe cabinets' }
      ]
    }
  ];
})();