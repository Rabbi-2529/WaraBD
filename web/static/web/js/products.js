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

  /* No products in the database: the shop is empty (no built-in demo product). */
  window.__WARA_PRODUCTS_SOURCE = 'none';
  return [];
})();