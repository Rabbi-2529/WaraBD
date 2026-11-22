/* Order edit page: district → thana dropdowns (Select2) in "Shipping Address".
   Data: <script id="order-locations"> (districts with their thanas). An old order whose
   district / thana is not in the list keeps its value. */
(function ($) {
  "use strict";
  if (!$ || !$.fn || !$.fn.select2) return;
  $(function () {
    var dEl = document.querySelector("select[data-order-district]");
    var tEl = document.querySelector("select[data-order-thana]");
    var src = document.getElementById("order-locations");
    if (!dEl || !tEl || !src) return;
    var data = [];
    try { data = JSON.parse(src.textContent) || []; } catch (e) { data = []; }
    var byName = {};
    data.forEach(function (d) { byName[d.v.toLowerCase()] = d; });
    var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    var opt = function (v, l) { return '<option value="' + esc(v) + '">' + esc(l) + "</option>"; };

    var keepD = dEl.dataset.selected || "", keepT = tEl.dataset.selected || "";
    dEl.innerHTML = opt("", "Select district") + data.map(function (d) { return opt(d.v, d.v); }).join("") +
      (keepD && !byName[keepD.toLowerCase()] ? opt(keepD, keepD + " (not in list)") : "");
    dEl.value = byName[keepD.toLowerCase()] ? byName[keepD.toLowerCase()].v : keepD;

    function fill(selected) {
      var d = byName[(dEl.value || "").toLowerCase()];
      var list = d ? d.t : [];
      tEl.innerHTML = opt("", d ? "Select thana / upazila" : "Select district first") + list.map(function (t) { return opt(t[0], t[0]); }).join("");
      if (selected) {
        var hit = list.filter(function (t) { return t[0].toLowerCase() === selected.toLowerCase(); })[0];
        if (!hit) tEl.insertAdjacentHTML("beforeend", opt(selected, selected + " (not in list)"));
        tEl.value = hit ? hit[0] : selected;
      }
      $(tEl).trigger("change.select2");
    }
    fill(keepT);
    $(dEl).select2({ width: "100%" }).on("change", function () { fill(""); });
    $(tEl).select2({ width: "100%" });
  });
})(window.django && window.django.jQuery);
