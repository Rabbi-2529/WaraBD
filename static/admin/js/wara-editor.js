/* CKEditor 5 on admin text areas marked data-rich-editor ("full" or "compact").
   Pictures are uploaded to data-upload-url with the Django CSRF token. */
(function () {
  "use strict";

  function csrfToken() {
    var input = document.querySelector("[name=csrfmiddlewaretoken]");
    if (input && input.value) return input.value;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function UploadAdapter(loader, url) {
    this.loader = loader;
    this.url = url;
  }
  UploadAdapter.prototype.upload = function () {
    var url = this.url;
    var self = this;
    return this.loader.file.then(function (file) {
      return new Promise(function (resolve, reject) {
        var xhr = (self.xhr = new XMLHttpRequest());
        xhr.open("POST", url, true);
        xhr.setRequestHeader("X-CSRFToken", csrfToken());
        xhr.responseType = "json";
        xhr.addEventListener("error", function () { reject("Upload failed. Check your connection."); });
        xhr.addEventListener("abort", function () { reject(); });
        xhr.addEventListener("load", function () {
          var res = xhr.response || {};
          if (xhr.status !== 200 || !res.url) return reject(res.error || "Upload failed.");
          resolve({ default: res.url });
        });
        if (xhr.upload) {
          xhr.upload.addEventListener("progress", function (e) {
            if (e.lengthComputable) { self.loader.uploadTotal = e.total; self.loader.uploaded = e.loaded; }
          });
        }
        var data = new FormData();
        data.append("upload", file);
        xhr.send(data);
      });
    });
  };
  UploadAdapter.prototype.abort = function () { if (this.xhr) this.xhr.abort(); };

  var TOOLBARS = {
    full: ["heading", "|", "bold", "italic", "link", "bulletedList", "numberedList", "|",
           "blockQuote", "insertTable", "uploadImage", "|", "outdent", "indent", "|", "undo", "redo"],
    compact: ["bold", "italic", "link", "bulletedList", "numberedList", "|", "undo", "redo"]
  };

  function start(textarea) {
    if (textarea.dataset.editorReady || !window.ClassicEditor) return;
    textarea.dataset.editorReady = "1";
    var mode = textarea.dataset.richEditor === "compact" ? "compact" : "full";
    var uploadUrl = textarea.dataset.uploadUrl;
    window.ClassicEditor.create(textarea, {
      toolbar: { items: TOOLBARS[mode], shouldNotGroupWhenFull: false },
      heading: {
        options: [
          { model: "paragraph", title: "Paragraph", class: "ck-heading_paragraph" },
          { model: "heading2", view: "h2", title: "Heading", class: "ck-heading_heading2" },
          { model: "heading3", view: "h3", title: "Sub heading", class: "ck-heading_heading3" }
        ]
      },
      image: { toolbar: ["imageTextAlternative", "|", "imageStyle:inline", "imageStyle:block", "imageStyle:side"] },
      table: { contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"] },
      link: { addTargetToExternalLinks: true },
      placeholder: textarea.getAttribute("placeholder") || ""
    }).then(function (editor) {
      if (uploadUrl) {
        editor.plugins.get("FileRepository").createUploadAdapter = function (loader) {
          return new UploadAdapter(loader, uploadUrl);
        };
      }
      var root = editor.ui.view.element;
      root.classList.add("wara-editor", "wara-editor-" + mode);
      if (textarea.getAttribute("lang")) {
        editor.editing.view.change(function (writer) {
          writer.setAttribute("lang", textarea.getAttribute("lang"), editor.editing.view.document.getRoot());
        });
      }
      // Keep the hidden textarea current (some scripts read it before submit).
      editor.model.document.on("change:data", function () { textarea.value = editor.getData(); });
      // Other scripts (the translate buttons) reach the editor through its textarea.
      textarea._waraEditor = editor;
      textarea.dispatchEvent(new CustomEvent("wara:editor-ready", { bubbles: true }));
    }).catch(function (err) {
      textarea.dataset.editorReady = "";
      console.error("CKEditor failed to start", err);
    });
  }

  function startAll(root) {
    (root || document).querySelectorAll("textarea[data-rich-editor]").forEach(function (el) {
      // Skip the hidden template row Django keeps for "Add another".
      if (el.closest(".empty-form") || el.name.indexOf("__prefix__") !== -1) return;
      start(el);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { startAll(); });
  else startAll();

  // New inline rows ("Add another …")
  document.addEventListener("formset:added", function (e) { startAll(e.target); });
})();
