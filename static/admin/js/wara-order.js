/* Admin → Orders → Create order (templates/admin/web/order/add_form.html).
   - Mobile number first: numbers only, Bangladeshi format; a known number fills in the customer.
   - District → thana dropdowns (Select2); the delivery charge follows them unless typed by hand.
   - Product search (Select2 + /admin/web/order/product-search/) adds order lines. */
(function ($) {
  "use strict";
  if (!$ || !$.fn || !$.fn.select2) return;
  $(function () {
  var form = document.getElementById("order_form");
  if (!form || !form.classList.contains("oc")) return;

  var BN = "০১২৩৪৫৬৭৮৯";
  var PHONE_RE = /^01[3-9]\d{8}$/;
  var $q = function (sel, root) { return (root || document).querySelector(sel); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var money = function (n) {
    var v = Math.round((Number(n) || 0) * 100) / 100;
    return "৳" + v.toLocaleString("en-IN", { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 });
  };
  var readJSON = function (id) {
    var el = document.getElementById(id);
    try { return el ? JSON.parse(el.textContent) || [] : []; } catch (e) { return []; }
  };

  /* ---------- Numbers only (mobile + sender number) ---------- */
  function digitsOnly(value) {
    var s = String(value || "").replace(/[০-৯]/g, function (d) { return BN.indexOf(d); }).replace(/\D/g, "");
    if (s.length > 11 && s.indexOf("880") === 0) s = s.slice(2);      // pasted +8801XXXXXXXXX
    return s.slice(0, 11);
  }
  function bindDigits(input) {
    input.addEventListener("input", function () {
      var clean = digitsOnly(input.value);
      if (clean !== input.value) input.value = clean;
    });
    input.addEventListener("keypress", function (e) {
      if (e.key && e.key.length === 1 && !/[0-9০-৯]/.test(e.key)) e.preventDefault();
    });
  }

  /* ---------- Customer lookup ---------- */
  var phone = $q("#id_phone"), phoneState = $q("#phoneState"), card = $q("#customerCard");
  var nameInput = $q("#id_full_name"), emailInput = $q("#id_email"), addressInput = $q("#id_address_line1");
  var lastLookup = "", lookupTimer = null;

  function setState(kind, text) {
    phoneState.className = "oc-phone-state " + (kind || "");
    phoneState.textContent = text || "";
    phone.closest(".wf-field").classList.toggle("has-error", kind === "bad");
  }

  function useAddress(a) {
    if (!a) return;
    if (a.name) nameInput.value = a.name;
    setLocation(a.district, a.thana);
    if (a.address) addressInput.value = a.address;
  }

  function showCustomer(data) {
    card.hidden = false;
    if (!data.found) {
      card.innerHTML = '<div class="oc-cust new"><span class="oc-badge">New customer</span><span>No orders with this number yet. Type the details below.</span></div>';
      return;
    }
    var c = data.customer || {}, o = data.orders || {}, fill = data.fill || {};
    var name = c.name || fill.name || "Customer";
    var bits = [];
    if (c.since) bits.push("Account since " + esc(c.since));
    bits.push(o.count + (o.count === 1 ? " order" : " orders"));
    if (Number(o.spent)) bits.push(money(o.spent) + " spent");
    var html = '<div class="oc-cust found">' +
      '<div class="oc-cust-top"><span class="oc-avatar">' + esc(name.charAt(0).toUpperCase()) + '</span>' +
      '<div><strong>' + esc(name) + '</strong><span>' + bits.join(" · ") + (c.email ? " · " + esc(c.email) : "") + '</span></div>' +
      '<span class="oc-badge ok"><i class="bx bx-check"></i> Returning customer</span></div>';
    if (c.active === false) html += '<p class="oc-warn"><i class="bx bx-block"></i> This customer is blocked from logging in.</p>';
    if (o.last) {
      html += '<p class="oc-last"><i class="bx bx-receipt"></i> Last order <b>' + esc(o.last.number) + '</b> · ' + esc(o.last.date) +
        ' · ' + esc(o.last.status) + ' · ' + money(o.last.total) + '</p>';
    }
    // The last order's address first (it is filled in), then the saved addresses.
    var addresses = [];
    var key = function (a) { return [a.address, a.thana, a.district].join("|").toLowerCase(); };
    if (o.last && fill.district) {
      addresses.push({ label: "Last order", name: fill.name, district: fill.district, thana: fill.thana, address: fill.address });
    }
    (data.addresses || []).forEach(function (a) {
      if (!addresses.some(function (b) { return key(b) === key(a); })) addresses.push(a);
    });
    if (addresses.length) {
      html += '<div class="oc-addrs">' + addresses.map(function (a, i) {
        return '<button type="button" class="oc-addr" data-addr="' + i + '"><span><b>' + esc(a.label || ("Address " + (i + 1))) + '</b>' +
          (a.default ? ' <em>default</em>' : '') + '<br>' + esc([a.address, a.thana, a.district].filter(Boolean).join(", ")) +
          '</span><span class="oc-use">Use</span></button>';
      }).join("") + '</div>';
    }
    card.innerHTML = html + '</div>';
    Array.prototype.forEach.call(card.querySelectorAll("[data-addr]"), function (btn) {
      btn.addEventListener("click", function () {
        useAddress(addresses[+btn.dataset.addr]);
        card.querySelectorAll(".oc-addr").forEach(function (b) { b.classList.toggle("on", b === btn); });
      });
    });
    // Fill the form from the last order (name, email, district, thana, address).
    if (fill.name) nameInput.value = fill.name;
    if (fill.email) emailInput.value = fill.email;
    if (fill.district) setLocation(fill.district, fill.thana);
    if (fill.address) addressInput.value = fill.address;
    if (addresses.length) card.querySelector(".oc-addr").classList.add("on");
  }

  function lookup(number) {
    if (number === lastLookup) return;
    lastLookup = number;
    setState("busy", "Checking…");
    fetch(form.dataset.lookupUrl + "?phone=" + encodeURIComponent(number), { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (digitsOnly(phone.value) !== number) return;
        if (!data.ok) { setState("bad", data.error || "Not a valid number"); return; }
        setState("ok", data.found ? "Customer found" : "Valid number");
        showCustomer(data);
      })
      .catch(function () { setState("", "Could not check the number"); lastLookup = ""; });
  }

  function onPhone() {
    var number = digitsOnly(phone.value);
    clearTimeout(lookupTimer);
    if (number.length < 11) {
      card.hidden = true;
      lastLookup = "";
      setState(number ? "" : "", number ? number.length + " / 11" : "");
      if (number.length >= 3 && !/^01[3-9]/.test(number)) setState("bad", "Must start with 013 – 019");
      return;
    }
    if (!PHONE_RE.test(number)) { card.hidden = true; setState("bad", "Not a Bangladeshi mobile number"); return; }
    lookupTimer = setTimeout(function () { lookup(number); }, 150);
  }
  bindDigits(phone);
  phone.addEventListener("input", onPhone);
  document.querySelectorAll("input[data-digits]").forEach(bindDigits);

  /* ---------- District → thana, delivery charge ---------- */
  var districts = readJSON("order-locations");
  var byName = {};
  districts.forEach(function (d) { byName[d.v.toLowerCase()] = d; });
  var districtEl = $q("#id_city"), thanaEl = $q("#id_thana");
  var shipping = $q("#id_shipping"), shipAuto = $q("#shipAuto"), quoteBox = $q("#deliveryQuote");
  var autoShip = shipping.value === "";

  function opt(value, label) { return '<option value="' + esc(value) + '">' + esc(label) + "</option>"; }
  districtEl.innerHTML = opt("", "Select district") + districts.map(function (d) {
    return opt(d.v, d.v === d.l ? d.v : d.v + " — " + d.l);
  }).join("");

  function currentDistrict() { return byName[(districtEl.value || "").toLowerCase()] || null; }
  function fillThanas(selected) {
    var d = currentDistrict();
    thanaEl.innerHTML = opt("", d ? "Select thana / upazila" : "Select district first") +
      (d ? d.t.map(function (t) { return opt(t[0], t[0] === t[1] ? t[0] : t[0] + " — " + t[1]); }).join("") : "");
    thanaEl.disabled = !d;
    if (selected && d) {
      var match = d.t.filter(function (t) { return t[0].toLowerCase() === String(selected).toLowerCase(); })[0];
      thanaEl.value = match ? match[0] : "";
    }
    $(thanaEl).trigger("change.select2");
  }
  function fee() {
    var d = currentDistrict();
    if (!d) return null;
    var t = d.t.filter(function (t) { return t[0] === thanaEl.value; })[0];
    return t && t[2] != null ? t[2] : d.f;
  }
  function paintQuote() {
    var d = currentDistrict(), f = fee();
    if (!d) {
      quoteBox.innerHTML = '<i class="bx bx-package"></i><span>Pick a district to see the delivery charge.</span>';
    } else {
      quoteBox.innerHTML = '<i class="bx bx-package"></i><span>Delivery to <b>' + esc((thanaEl.value ? thanaEl.value + ", " : "") + d.v) +
        "</b>: <b>" + money(f) + "</b>" + (d.e ? " · " + esc(d.e) : "") + "</span>";
    }
    if (autoShip) shipping.value = f == null ? "" : f;
    shipAuto.textContent = autoShip ? "auto" : "typed — click to reset";
    shipAuto.classList.toggle("manual", !autoShip);
    totals();
  }
  function setLocation(district, thana) {
    var d = byName[String(district || "").toLowerCase()];
    districtEl.value = d ? d.v : "";
    $(districtEl).trigger("change.select2");
    fillThanas(thana);
    paintQuote();
  }

  $(districtEl).select2({ width: "100%", placeholder: "Select district" });
  $(thanaEl).select2({ width: "100%", placeholder: "Select thana / upazila" });
  $(districtEl).on("change", function () { fillThanas(""); paintQuote(); });
  $(thanaEl).on("change", paintQuote);
  shipping.addEventListener("input", function () { autoShip = shipping.value === ""; shipAuto.textContent = autoShip ? "auto" : "typed — click to reset"; shipAuto.classList.toggle("manual", !autoShip); totals(); });
  shipAuto.addEventListener("click", function () { autoShip = true; paintQuote(); });

  /* ---------- Product lines ---------- */
  var lines = $q("#orderLines"), empty = $q("#linesEmpty");

  function stockText(p) {
    if (p.active === false) return '<span class="oc-stock off">Hidden on the shop</span>';
    return p.stock > 0 ? '<span class="oc-stock">' + p.stock + " in stock</span>" : '<span class="oc-stock out">Out of stock</span>';
  }
  function thumb(p) {
    return p.image ? '<img src="' + esc(p.image) + '" alt="">' : '<span class="oc-noimg"><i class="bx bx-image"></i></span>';
  }
  function addLine(p, qty, price) {
    var existing = lines.querySelector('tr[data-id="' + p.id + '"]');
    if (existing) {
      var q = existing.querySelector('input[name="item_qty"]');
      q.value = Math.min(999, (parseInt(q.value, 10) || 0) + (qty || 1));
      totals();
      existing.classList.remove("flash"); void existing.offsetWidth; existing.classList.add("flash");
      return;
    }
    var tr = document.createElement("tr");
    tr.dataset.id = p.id;
    tr.dataset.stock = p.stock;
    tr.innerHTML =
      '<td><div class="oc-prod">' + thumb(p) + '<div><strong>' + esc(p.name) + "</strong><span>" +
      (p.sku ? esc(p.sku) + " · " : "") + stockText(p) + '</span><em class="oc-short" hidden></em></div></div>' +
      '<input type="hidden" name="item_product" value="' + esc(p.id) + '"></td>' +
      '<td class="num"><input type="number" name="item_price" min="0" step="0.01" value="' + esc(price != null ? price : p.price) + '" class="oc-price"></td>' +
      '<td class="num"><div class="oc-qty"><button type="button" data-step="-1" aria-label="Less">−</button>' +
      '<input type="number" name="item_qty" min="1" max="999" value="' + esc(qty || 1) + '">' +
      '<button type="button" data-step="1" aria-label="More">+</button></div></td>' +
      '<td class="num oc-line-total"></td>' +
      '<td><button type="button" class="oc-remove" data-remove aria-label="Remove"><i class="bx bx-trash"></i></button></td>';
    lines.appendChild(tr);
    totals();
  }
  lines.addEventListener("click", function (e) {
    var row = e.target.closest("tr");
    if (!row) return;
    var step = e.target.closest("[data-step]");
    if (step) {
      var q = row.querySelector('input[name="item_qty"]');
      q.value = Math.max(1, Math.min(999, (parseInt(q.value, 10) || 1) + Number(step.dataset.step)));
      totals();
    }
    if (e.target.closest("[data-remove]")) { row.remove(); totals(); }
  });
  lines.addEventListener("input", totals);

  function totals() {
    var sub = 0, count = 0;
    Array.prototype.forEach.call(lines.rows, function (row) {
      var qty = Math.max(0, parseInt(row.querySelector('input[name="item_qty"]').value, 10) || 0);
      var price = Math.max(0, parseFloat(row.querySelector('input[name="item_price"]').value) || 0);
      sub += qty * price;
      count += qty;
      row.querySelector(".oc-line-total").textContent = money(qty * price);
      var stock = parseInt(row.dataset.stock, 10) || 0, short = row.querySelector(".oc-short");
      short.hidden = qty <= stock || stock <= 0;
      short.textContent = "Only " + stock + " in stock";
    });
    empty.hidden = lines.rows.length > 0;
    var ship = Math.max(0, parseFloat(shipping.value) || 0);
    var dValue = Math.max(0, parseFloat(discountValue.value) || 0);
    var percent = (form.querySelector('input[name="discount_type"]:checked') || {}).value === "percent";
    var disc = percent ? sub * Math.min(dValue, 100) / 100 : Math.min(dValue, sub);
    disc = Math.round(disc * 100) / 100;
    discountLine.hidden = !disc;
    $q("#discountAmount").textContent = "− " + money(disc) + (percent && dValue ? " (" + Math.min(dValue, 100) + "%)" : "");
    $q("#subtotal").textContent = money(sub);
    $q("#itemCount").textContent = count ? "(" + count + (count === 1 ? " item)" : " items)") : "";
    $q("#grandTotal").textContent = money(sub - disc + ship);
  }
  var discountValue = $q("#id_discount_value"), discountLine = $q("#discountLine");
  discountValue.addEventListener("input", totals);
  form.addEventListener("change", function (e) { if (e.target.name === "discount_type") totals(); });

  function resultHTML(p) {
    if (p.loading) return p.text;
    return $('<div class="oc-result">' + thumb(p) + '<div><strong>' + esc(p.name) + "</strong><span>" +
      (p.sku ? esc(p.sku) + " · " : "") + stockText(p) + '</span></div><b>' + money(p.price) + "</b></div>");
  }
  $("#productSearch").select2({
    width: "100%",
    placeholder: "Search product by name, SKU or model number…",
    ajax: {
      url: form.dataset.searchUrl,
      dataType: "json",
      delay: 200,
      data: function (params) { return { q: params.term || "" }; },
      processResults: function (data) { return { results: data.results || [] }; },
      cache: true
    },
    minimumInputLength: 0,
    templateResult: resultHTML,
    templateSelection: function () { return "Search product by name, SKU or model number…"; },
    language: { noResults: function () { return "No product found"; }, searching: function () { return "Searching…"; } }
  }).on("select2:select", function (e) {
    addLine(e.params.data, 1);
    $(this).val(null).trigger("change");
  });

  /* ---------- Payment ---------- */
  var mobilePay = $q("#mobilePay");
  function paintPay() {
    var m = (form.querySelector('input[name="payment_method"]:checked') || {}).value;
    mobilePay.hidden = m !== "bkash" && m !== "nagad";
  }
  form.addEventListener("change", function (e) { if (e.target.name === "payment_method") paintPay(); });

  /* ---------- Check before sending ---------- */
  form.addEventListener("submit", function (e) {
    var problems = [];
    function mark(input, bad) {
      var field = input.closest(".wf-field");
      if (field) field.classList.toggle("has-error", bad);
      if (bad) problems.push(input);
    }
    mark(phone, !PHONE_RE.test(digitsOnly(phone.value)));
    mark(nameInput, nameInput.value.trim().length < 2);
    mark(districtEl, !districtEl.value);
    mark(thanaEl, !thanaEl.value);
    mark(addressInput, addressInput.value.trim().length < 5);
    if (!lines.rows.length) {
      problems.push($q("#productSearch"));
      empty.classList.add("bad");
    }
    if (problems.length) {
      e.preventDefault();
      var first = problems[0];
      (first.closest(".wf-card") || first).scrollIntoView({ behavior: "smooth", block: "center" });
      if (first.focus && first.type !== "select-one") first.focus();
    }
  });

  /* ---------- Start ---------- */
  setLocation(districtEl.dataset.selected, thanaEl.dataset.selected);
  readJSON("order-lines").forEach(function (p) { addLine(p, parseInt(p.qty, 10) || 1, p.price); });
  paintPay();
  totals();
  if (PHONE_RE.test(digitsOnly(phone.value))) onPhone();
  });
})(window.django && window.django.jQuery);
