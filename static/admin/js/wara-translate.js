/* English → বাংলা in the admin, with Google Translate (web/translate.py).

   Every form box named something_bn that has a something_en partner gets a
   "Translate from English" button. When an English box is finished and its বাংলা
   box is still empty, the বাংলা is filled in automatically (never overwritten).
   Works with plain boxes, CKEditor boxes, the FAQ editor and the product list editors
   (only the words are translated: icons, "Q:" / "A:", "Works with:" stay as they are). */
(function () {
  "use strict";
  var meta = document.querySelector('meta[name="wara-translate"]');
  if (!meta) return;
  var URL = meta.getAttribute("content");
  var READY = meta.dataset.ready === "1";
  var SETTINGS = meta.dataset.settings || "";

  function csrf() {
    var i = document.querySelector("[name=csrfmiddlewaretoken]");
    if (i && i.value) return i.value;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function call(texts, format) {
    return fetch(URL, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify({ texts: texts, format: format })
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.error) throw new Error(d.error);
      return d.translations || [];
    });
  }

  function lines(t) { return String(t || "").replace(/\r\n?/g, "\n").split("\n").map(function (s) { return s.trim(); }).filter(Boolean); }
  function stripTags(h) { var d = document.createElement("div"); d.innerHTML = h || ""; return (d.textContent || "").trim(); }

  /* What to send for each kind of box, and how to put the answer back together. */
  function plan(kind, text) {
    var parts = [], build;
    function slot(s) { s = String(s || "").trim(); if (!s) return -1; parts.push(s); return parts.length - 1; }
    function got(tr, i) { return i < 0 ? "" : (tr[i] || ""); }
    if (kind === "html" || kind === "text") {
      var i0 = slot(text);
      build = function (tr) { return got(tr, i0); };
      return { parts: parts, build: build, format: kind };
    }
    var rows = [];
    if (kind === "highlights") {
      rows = lines(text).map(function (l) { return slot(l); });
      build = function (tr) { return rows.map(function (i) { return got(tr, i); }).filter(Boolean).join("\n"); };
    } else if (kind === "specs") {
      rows = lines(text).map(function (l) {
        var i = l.indexOf(":");
        return i < 0 ? [slot(l), -1] : [slot(l.slice(0, i)), slot(l.slice(i + 1))];
      });
      build = function (tr) {
        return rows.map(function (r) { return got(tr, r[0]).replace(/:/g, " ") + ": " + got(tr, r[1]); }).join("\n");
      };
    } else if (kind === "features") {
      rows = lines(text).map(function (l) {
        var p = l.split("|").map(function (s) { return s.trim(); });
        if (p.length >= 3) return [p[0], slot(p[1]), slot(p.slice(2).join(" | "))];
        if (p.length === 2) return ["check", slot(p[0]), slot(p[1])];
        return ["check", slot(p[0]), -1];
      });
      build = function (tr) {
        return rows.map(function (r) { return r[0] + " | " + got(tr, r[1]).replace(/\|/g, "/") + " | " + got(tr, r[2]); }).join("\n");
      };
    } else if (kind === "steps") {
      rows = lines(text).map(function (l) {
        var i = l.indexOf("|");
        return i < 0 ? [-1, slot(l)] : [slot(l.slice(0, i)), slot(l.slice(i + 1))];
      });
      build = function (tr) {
        return rows.map(function (r) {
          var t = got(tr, r[0]).replace(/\|/g, "/"), x = got(tr, r[1]);
          return t ? t + " | " + x : x.replace(/\|/g, "/");
        }).join("\n");
      };
    } else if (kind === "applications") {
      rows = lines(text).map(function (l) {
        var i = l.indexOf(":");
        return i < 0 ? null : [l.slice(0, i).trim(), slot(l.slice(i + 1))];
      }).filter(Boolean);
      build = function (tr) { return rows.map(function (r) { return r[0] + ": " + got(tr, r[1]).replace(/،/g, ","); }).join("\n"); };
    } else if (kind === "faq") {
      var cur = null;
      String(text || "").replace(/\r\n?/g, "\n").split("\n").concat([""]).forEach(function (raw) {
        var l = raw.trim(), h = l.slice(0, 2).toUpperCase();
        if (h === "Q:") { if (cur) rows.push(cur); cur = { q: l.slice(2).trim(), a: [] }; }
        else if (h === "A:" && cur) cur.a.push(l.slice(2).trim());
        else if (!l) { if (cur) rows.push(cur); cur = null; }
        else if (cur) cur.a.push(l);
      });
      rows = rows.map(function (r) { return [slot(r.q), slot(r.a.join("\n"))]; });
      build = function (tr) {
        return rows.map(function (r) { return "Q: " + got(tr, r[0]).replace(/\n/g, " ") + "\nA: " + got(tr, r[1]); }).join("\n\n");
      };
    }
    return { parts: parts, build: build, format: "text" };
  }

  function kindOf(el) {
    if (el.hasAttribute("data-rich-editor")) return "html";
    if (el.hasAttribute("data-faq-editor")) return "faq";
    if (el.hasAttribute("data-list-editor")) return el.getAttribute("data-list-editor");
    return "text";
  }
  function isEmpty(el) {
    var v = el.value || "";
    return kindOf(el) === "html" ? !stripTags(v) : !v.trim();
  }
  function setValue(el, value) {
    if (el._waraEditor) el._waraEditor.setData(value);
    el.value = value;
    el.dispatchEvent(new CustomEvent("wara:reload"));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function note(btn, text, bad) {
    var n = btn.nextElementSibling && btn.nextElementSibling.classList.contains("wt-note") ? btn.nextElementSibling : null;
    if (!n) { n = document.createElement("span"); n.className = "wt-note"; btn.insertAdjacentElement("afterend", n); }
    n.className = "wt-note" + (bad ? " bad" : "");
    n.innerHTML = text;
    clearTimeout(n._t);
    if (!bad) n._t = setTimeout(function () { n.innerHTML = ""; }, 3000);
  }

  function translatePair(pair, auto) {
    var en = pair.en, bn = pair.bn, btn = pair.btn;
    if (!READY) {
      if (!auto) note(btn, 'Add your Google Translate API key in <a href="' + SETTINGS + '">Site settings → Translation</a> first.', true);
      return;
    }
    if (isEmpty(en)) { if (!auto) note(btn, "The English box is empty.", true); return; }
    if (!auto && !isEmpty(bn) && !window.confirm("Replace the বাংলা text with a new translation?")) return;
    var p = plan(kindOf(bn) === "html" ? "html" : kindOf(bn), en.value);
    if (!p.parts.length) return;
    btn.disabled = true;
    var label = btn.innerHTML;
    btn.innerHTML = "Translating…";
    call(p.parts, p.format).then(function (tr) {
      if (auto && !isEmpty(bn)) return;  // typed in the meantime: keep it
      setValue(bn, p.build(tr));
      note(btn, auto ? "✓ Filled in from English, please check it" : "✓ Translated, please check it");
    }).catch(function (e) {
      note(btn, e.message || "Translation failed.", true);
    }).then(function () { btn.disabled = false; btn.innerHTML = label; });
  }

  function anchorFor(bn) {
    var label = bn.id ? document.querySelector('label[for="' + bn.id + '"]') : null;
    if (label) return { el: label, where: "beforeend" };
    var raw = bn.closest(".faq-ed-raw");
    if (raw && raw.previousElementSibling) return { el: raw.previousElementSibling, where: "beforebegin" };
    return { el: bn, where: "beforebegin" };
  }

  function watchEnglish(pair) {
    var en = pair.en, kind = kindOf(en);
    var maybe = function () { if (READY && isEmpty(pair.bn) && !isEmpty(en)) translatePair(pair, true); };
    if (kind === "html") {
      var hook = function () {
        if (!en._waraEditor) return;
        en._waraEditor.ui.focusTracker.on("change:isFocused", function (evt, name, focused) { if (!focused) maybe(); });
      };
      if (en._waraEditor) hook(); else en.addEventListener("wara:editor-ready", hook, { once: true });
    } else if (kind !== "text") {
      var box = en.closest(".faq-ed-raw");
      var target = box && box.previousElementSibling ? box.previousElementSibling : en.parentNode;
      target.addEventListener("focusout", function () { setTimeout(function () { if (!target.contains(document.activeElement)) maybe(); }, 50); });
    } else {
      en.addEventListener("change", maybe);
    }
  }

  function start() {
    var seen = 0;
    document.querySelectorAll("form [name$='_bn']").forEach(function (bn) {
      if (bn.dataset.wtReady || bn.type === "hidden" || bn.type === "file" || bn.type === "checkbox") return;
      var form = bn.form || bn.closest("form");
      var en = form && form.querySelector('[name="' + bn.name.replace(/_bn$/, "_en") + '"]');
      if (!en || (bn.name || "").indexOf("__prefix__") !== -1) return;
      bn.dataset.wtReady = "1";
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "wt-btn";
      btn.title = READY ? "Fill this বাংলা box from the English one (Google Translate)" : "Needs a Google Translate API key in Site settings";
      var inTable = !!bn.closest("td");  // gallery captions etc.: a small button that fits the cell
      btn.innerHTML = inTable ? "⇄" : "⇄ Translate from English";
      if (inTable) { btn.className += " wt-mini"; btn.title = "Translate from English"; }
      var a = inTable ? { el: bn, where: "afterend" } : anchorFor(bn);
      a.el.insertAdjacentElement(a.where, btn);
      var pair = { en: en, bn: bn, btn: btn };
      btn.addEventListener("click", function (e) { e.preventDefault(); translatePair(pair, false); });
      watchEnglish(pair);
      seen++;
    });
    if (seen && !document.getElementById("wt-style")) {
      var s = document.createElement("style");
      s.id = "wt-style";
      s.textContent =
        ".wt-btn{display:inline-flex;align-items:center;gap:4px;margin:0 0 0 8px;padding:2px 9px !important;border:1px solid #f6c4ca !important;" +
        "border-radius:999px !important;background:#fff !important;color:#d7182a !important;font-size:11.5px !important;font-weight:600 !important;" +
        "line-height:1.6;cursor:pointer;vertical-align:middle;height:auto !important;box-shadow:none !important}" +
        ".wt-mini{margin:4px 0 0 !important;padding:1px 8px !important;font-size:13px !important}td .wt-note{display:block;margin:2px 0 0}" +
        ".wt-btn:hover{background:#fdecee !important}.wt-btn[disabled]{opacity:.6;cursor:wait}" +
        ".wt-note{margin-left:8px;font-size:11.5px;font-weight:600;color:#15803d}.wt-note.bad{color:#b31322}.wt-note a{color:#b31322;text-decoration:underline}";
      document.head.appendChild(s);
    }
  }

  // After the other editors (CKEditor, FAQ, lists) have built their boxes.
  document.addEventListener("formset:added", function () { setTimeout(start, 0); });  // "Add another" rows
  if (document.readyState === "complete") setTimeout(start, 0);
  else window.addEventListener("load", function () { setTimeout(start, 0); });
})();
