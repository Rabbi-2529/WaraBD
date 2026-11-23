/* FAQ editor: turns <textarea data-faq-editor> into question / answer rows.
   The rows are written back into the textarea as
       Q: question
       A: answer
   blocks (one blank line between them), which is what the server reads —
   so the page still works if this script does not load. */
(function () {
  "use strict";

  function parse(text) {
    var rows = [], cur = null;
    String(text || "").replace(/\r\n?/g, "\n").split("\n").concat([""]).forEach(function (raw) {
      var line = raw.trim(), head = line.slice(0, 2).toUpperCase();
      if (head === "Q:") {
        if (cur) rows.push(cur);
        cur = { q: line.slice(2).trim(), a: "" };
      } else if (head === "A:" && cur) {
        cur.a = (cur.a + "\n" + line.slice(2).trim()).trim();
      } else if (!line) {
        if (cur) rows.push(cur);
        cur = null;
      } else if (cur) {
        cur.a = (cur.a + "\n" + line).trim();
      } else {
        rows.push({ q: line, a: "" });
      }
    });
    return rows;
  }

  function serialize(rows) {
    return rows.filter(function (r) { return r.q.trim() || r.a.trim(); }).map(function (r) {
      var answer = r.a.split("\n").map(function (s) { return s.trim(); }).filter(Boolean);
      // A continuation line must not look like a new "Q:" / "A:" line.
      answer = answer.map(function (s, i) { return i && /^[qa]:/i.test(s) ? "- " + s : s; });
      return "Q: " + r.q.trim().replace(/\s*\n\s*/g, " ") + "\nA: " + answer.join("\n");
    }).join("\n\n");
  }

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function build(textarea) {
    if (textarea.dataset.faqReady || (textarea.id || "").indexOf("__prefix__") !== -1) return;
    textarea.dataset.faqReady = "1";
    var lang = textarea.getAttribute("lang") || "";
    var bn = lang === "bn";

    var box = el("div", "faq-ed");
    var list = el("div", "faq-ed-list");
    var empty = el("div", "faq-ed-empty", bn ? "No questions yet — or leave empty to show the English ones." : "No questions yet.");
    var foot = el("div", "faq-ed-foot");
    var add = el("button", "faq-ed-add", '<i class="bx bx-plus"></i> Add question');
    var toText = el("button", "faq-ed-text", "Edit as text");
    add.type = toText.type = "button";
    foot.appendChild(add);
    foot.appendChild(toText);
    box.appendChild(list);
    box.appendChild(empty);
    box.appendChild(foot);

    var raw = el("div", "faq-ed-raw");
    raw.hidden = true;
    var back = el("button", "faq-ed-text", "Back to question rows");
    back.type = "button";
    textarea.parentNode.insertBefore(box, textarea);
    textarea.parentNode.insertBefore(raw, textarea);
    raw.appendChild(textarea);
    raw.appendChild(back);

    function write() {
      var rows = Array.prototype.map.call(list.children, function (row) {
        return { q: row.querySelector(".faq-ed-q").value, a: row.querySelector(".faq-ed-a").value };
      });
      textarea.value = serialize(rows);
      Array.prototype.forEach.call(list.children, function (row, i) {
        row.querySelector(".faq-ed-num").textContent = i + 1;
        var q = row.querySelector(".faq-ed-q").value.trim(), a = row.querySelector(".faq-ed-a").value.trim();
        row.classList.toggle("bad", (!!q) !== (!!a) && row.dataset.touched === "1");
      });
      empty.hidden = list.children.length > 0;
    }

    function addRow(item, focus) {
      var row = el("div", "faq-ed-row");
      row.innerHTML =
        '<span class="faq-ed-num"></span>' +
        '<div class="faq-ed-fields">' +
        '<input type="text" class="faq-ed-q" placeholder="' + (bn ? "প্রশ্ন" : "Question") + '">' +
        '<textarea class="faq-ed-a" rows="2" placeholder="' + (bn ? "উত্তর" : "Answer") + '"></textarea>' +
        "</div>" +
        '<div class="faq-ed-tools">' +
        '<button type="button" data-move="-1" title="Move up" aria-label="Move up"><i class="bx bx-chevron-up"></i></button>' +
        '<button type="button" data-move="1" title="Move down" aria-label="Move down"><i class="bx bx-chevron-down"></i></button>' +
        '<button type="button" data-del title="Remove" aria-label="Remove"><i class="bx bx-trash"></i></button>' +
        "</div>";
      var q = row.querySelector(".faq-ed-q"), a = row.querySelector(".faq-ed-a");
      q.value = item.q || "";
      a.value = item.a || "";
      if (lang) { q.setAttribute("lang", lang); a.setAttribute("lang", lang); }
      list.appendChild(row);
      if (focus) q.focus();
    }

    function load() {
      list.innerHTML = "";
      parse(textarea.value).forEach(function (item) { addRow(item); });
      write();
    }

    list.addEventListener("input", function (e) {
      var row = e.target.closest(".faq-ed-row");
      if (row) row.dataset.touched = "1";
      write();
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

  function start(root) {
    (root || document).querySelectorAll("textarea[data-faq-editor]").forEach(build);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { start(); });
  else start();
  document.addEventListener("formset:added", function (e) { start(e.target); });
})();
