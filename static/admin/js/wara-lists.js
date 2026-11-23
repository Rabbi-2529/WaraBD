/* Row editors for the product lists (textarea[data-list-editor]).

   highlights    one box per point                      ->  Point
   specs         name + value                           ->  Name: Value
   features      icon + title + text                    ->  icon | Title | Text
   steps         title (optional) + text                ->  Title | Text
   applications  "Works with" + "Used in" (comma lists) ->  Works with: a, b / Used in: c, d

   The rows are written back into the textarea in the format on the right, which is
   what the server reads (web/forms.py), so the form still works without this script. */
(function () {
  "use strict";

  var ICONS = ["check", "keypad", "key", "lock", "unlock", "shield", "battery", "zap", "usb", "mobile",
    "wifioff", "eye", "users", "user", "clock", "refresh", "award", "truck", "home", "briefcase", "bed",
    "hospital", "box", "drawer", "archive", "tool", "ruler", "heart", "target", "alert", "info", "cash",
    "headset", "globe", "file", "book", "activity", "grid", "bag", "message"];

  function lines(text) {
    return String(text || "").replace(/\r\n?/g, "\n").split("\n").map(function (s) { return s.trim(); })
      .filter(Boolean);
  }
  function one(s) { return String(s || "").replace(/\s*\n\s*/g, " ").trim(); }

  var KINDS = {
    highlights: {
      add: "Add highlight", empty: "No highlights yet.",
      fields: [{ key: "text", ph: "e.g. Password & USB key unlock" }],
      parse: function (t) { return lines(t).map(function (l) { return { text: l }; }); },
      line: function (r) { return one(r.text); }
    },
    specs: {
      add: "Add specification", empty: "No specifications yet.",
      fields: [{ key: "label", ph: "Name, e.g. Model" }, { key: "value", ph: "Value, e.g. FT-SCL029" }],
      parse: function (t) {
        return lines(t).map(function (l) {
          var i = l.indexOf(":");
          return i < 0 ? { label: l, value: "" } : { label: l.slice(0, i).trim(), value: l.slice(i + 1).trim() };
        });
      },
      line: function (r) {
        var label = one(r.label).replace(/:/g, " "), value = one(r.value);
        return label || value ? label + ": " + value : "";
      }
    },
    features: {
      add: "Add feature", empty: "No features yet.",
      fields: [{ key: "icon", icon: true }, { key: "title", ph: "Title, e.g. Two password sets" },
               { key: "text", ph: "Short text", area: true }],
      parse: function (t) {
        return lines(t).map(function (l) {
          var p = l.split("|").map(function (s) { return s.trim(); });
          if (p.length >= 3) return { icon: p[0] || "check", title: p[1], text: p.slice(2).join(" | ") };
          if (p.length === 2) return { icon: "check", title: p[0], text: p[1] };
          return { icon: "check", title: p[0], text: "" };
        });
      },
      line: function (r) {
        var title = one(r.title).replace(/\|/g, "/"), text = one(r.text);
        return title || text ? (r.icon || "check") + " | " + title + " | " + text : "";
      }
    },
    steps: {
      add: "Add step", empty: "No steps yet.",
      fields: [{ key: "title", ph: "Step title (optional), e.g. Fit the lock" },
               { key: "text", ph: "What to do in this step", area: true }],
      parse: function (t) {
        return lines(t).map(function (l) {
          var i = l.indexOf("|");
          return i < 0 ? { title: "", text: l } : { title: l.slice(0, i).trim(), text: l.slice(i + 1).trim() };
        });
      },
      line: function (r) {
        var title = one(r.title).replace(/\|/g, "/"), text = one(r.text);
        if (!title && !text) return "";
        return title ? title + " | " + text : text.replace(/\|/g, "/");
      }
    }
  };

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  /* ---------- rows: highlights / specs / features / steps ---------- */
  function buildRows(textarea, kind) {
    var cfg = KINDS[kind], lang = textarea.getAttribute("lang") || "";
    var box = el("div", "faq-ed list-ed list-ed-" + kind);
    var list = el("div", "faq-ed-list");
    var empty = el("div", "faq-ed-empty", cfg.empty);
    var foot = el("div", "faq-ed-foot");
    var add = el("button", "faq-ed-add", '<i class="bx bx-plus"></i> ' + cfg.add);
    var toText = el("button", "faq-ed-text", "Edit as text");
    add.type = toText.type = "button";
    foot.appendChild(add); foot.appendChild(toText);
    box.appendChild(list); box.appendChild(empty); box.appendChild(foot);
    var raw = el("div", "faq-ed-raw");
    raw.hidden = true;
    var back = el("button", "faq-ed-text", "Back to rows");
    back.type = "button";
    textarea.parentNode.insertBefore(box, textarea);
    textarea.parentNode.insertBefore(raw, textarea);
    raw.appendChild(textarea);
    raw.appendChild(back);

    function write() {
      var out = [];
      Array.prototype.forEach.call(list.children, function (row, i) {
        row.querySelector(".faq-ed-num").textContent = i + 1;
        var data = {};
        cfg.fields.forEach(function (f) { data[f.key] = row.querySelector("[data-k='" + f.key + "']").value; });
        var l = cfg.line(data);
        if (l) out.push(l);
      });
      textarea.value = out.join("\n");
      empty.hidden = list.children.length > 0;
    }

    function control(f, value) {
      var c;
      if (f.icon) {
        c = document.createElement("select");
        var opts = ICONS.slice();
        if (value && opts.indexOf(value) < 0) opts.unshift(value);
        c.innerHTML = opts.map(function (n) { return '<option value="' + n + '">' + n + "</option>"; }).join("");
        c.value = value || "check";
        c.title = "Icon";
      } else if (f.area) {
        c = document.createElement("textarea");
        c.rows = 2;
      } else {
        c = document.createElement("input");
        c.type = "text";
      }
      if (!f.icon) { c.value = value || ""; c.placeholder = f.ph || ""; if (lang) c.setAttribute("lang", lang); }
      c.className = "list-ed-" + f.key;
      c.setAttribute("data-k", f.key);
      return c;
    }

    function addRow(data, focus) {
      var row = el("div", "faq-ed-row");
      var fields = el("div", "faq-ed-fields list-ed-fields");
      cfg.fields.forEach(function (f) { fields.appendChild(control(f, data[f.key])); });
      row.appendChild(el("span", "faq-ed-num"));
      row.appendChild(fields);
      row.appendChild(el("div", "faq-ed-tools",
        '<button type="button" data-move="-1" title="Move up" aria-label="Move up"><i class="bx bx-chevron-up"></i></button>' +
        '<button type="button" data-move="1" title="Move down" aria-label="Move down"><i class="bx bx-chevron-down"></i></button>' +
        '<button type="button" data-del title="Remove" aria-label="Remove"><i class="bx bx-trash"></i></button>'));
      list.appendChild(row);
      if (focus) { var first = fields.querySelector("input, textarea"); if (first) first.focus(); }
    }

    function load() {
      list.innerHTML = "";
      cfg.parse(textarea.value).forEach(function (r) { addRow(r); });
      write();
    }

    list.addEventListener("input", write);
    list.addEventListener("change", write);
    list.addEventListener("keydown", function (e) {
      // Enter in the last row's one-line box starts a new row (quick for lists of points).
      if (e.key !== "Enter" || e.target.tagName !== "INPUT") return;
      e.preventDefault();
      var row = e.target.closest(".faq-ed-row");
      if (row === list.lastElementChild) { addRow({}, true); write(); }
    });
    list.addEventListener("click", function (e) {
      var btn = e.target.closest("button");
      if (!btn) return;
      var row = btn.closest(".faq-ed-row");
      if (btn.hasAttribute("data-del")) row.remove();
      else if (btn.dataset.move === "-1" && row.previousElementSibling) list.insertBefore(row, row.previousElementSibling);
      else if (btn.dataset.move === "1" && row.nextElementSibling) list.insertBefore(row.nextElementSibling, row);
      write();
    });
    add.addEventListener("click", function () { addRow({}, true); write(); });
    toText.addEventListener("click", function () { box.hidden = true; raw.hidden = false; textarea.focus(); });
    back.addEventListener("click", function () { raw.hidden = true; box.hidden = false; load(); });
    textarea.addEventListener("wara:reload", load);  // text changed by another script (translate)
    load();
  }

  /* ---------- works with / used in ---------- */
  function buildApplications(textarea) {
    var lang = textarea.getAttribute("lang") || "";
    var values = { works: "", used: "" };
    lines(textarea.value).forEach(function (l) {
      var i = l.indexOf(":"), key = i < 0 ? "" : l.slice(0, i).trim().toLowerCase(), rest = i < 0 ? "" : l.slice(i + 1).trim();
      if (key === "works with") values.works = rest;
      if (key === "used in") values.used = rest;
    });
    var box = el("div", "faq-ed list-ed list-ed-applications");
    box.innerHTML =
      '<label class="list-ed-label">Works with <small>(e.g. Cabinets, Drawers, Lockers)</small></label>' +
      '<input type="text" data-k="works" placeholder="Separate with commas">' +
      '<label class="list-ed-label">Used in <small>(e.g. Kitchen, Office, Hotel)</small></label>' +
      '<input type="text" data-k="used" placeholder="Separate with commas">';
    var works = box.querySelector("[data-k='works']"), used = box.querySelector("[data-k='used']");
    works.value = values.works; used.value = values.used;
    if (lang) { works.setAttribute("lang", lang); used.setAttribute("lang", lang); }
    textarea.parentNode.insertBefore(box, textarea);
    textarea.hidden = true;
    function tidy(s) { return one(s).split(",").map(function (x) { return x.trim(); }).filter(Boolean).join(", "); }
    function write() {
      var out = [];
      if (tidy(works.value)) out.push("Works with: " + tidy(works.value));
      if (tidy(used.value)) out.push("Used in: " + tidy(used.value));
      textarea.value = out.join("\n");
    }
    box.addEventListener("input", write);
    textarea.addEventListener("wara:reload", function () {  // text changed by another script (translate)
      var v = { works: "", used: "" };
      lines(textarea.value).forEach(function (l) {
        var i = l.indexOf(":"), k = i < 0 ? "" : l.slice(0, i).trim().toLowerCase(), rest = i < 0 ? "" : l.slice(i + 1).trim();
        if (k === "works with") v.works = rest;
        if (k === "used in") v.used = rest;
      });
      works.value = v.works; used.value = v.used;
      write();
    });
    write();
  }

  function start(root) {
    (root || document).querySelectorAll("textarea[data-list-editor]").forEach(function (t) {
      if (t.dataset.listReady || (t.id || "").indexOf("__prefix__") !== -1) return;
      t.dataset.listReady = "1";
      var kind = t.getAttribute("data-list-editor");
      if (kind === "applications") buildApplications(t);
      else if (KINDS[kind]) buildRows(t, kind);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { start(); });
  else start();
})();
