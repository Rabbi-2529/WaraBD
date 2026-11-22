/* SEO keywords: Select2 "tags" box on <select multiple data-keyword-tags>.
   Keywords used on any product / category / page are offered as you type;
   a new one is added with Enter or a comma and saved as a keyword for everyone. */
(function ($) {
  "use strict";
  if (!$ || !$.fn || !$.fn.select2) return;

  function start(root) {
    $(root).find("select[data-keyword-tags]").each(function () {
      var el = this;
      if ((el.id || "").indexOf("__prefix__") !== -1 || $(el).data("select2")) return;
      $(el).select2({
        tags: true,
        tokenSeparators: [","],
        width: "100%",
        placeholder: "Type a keyword…",
        createTag: function (params) {
          var term = $.trim(params.term || "").replace(/\s+/g, " ");
          if (!term) return null;
          var lower = term.toLowerCase(), clash = false;
          $(el).find("option").each(function () { if (this.value.toLowerCase() === lower) clash = true; });
          return clash ? null : { id: term, text: term, newTag: true };
        },
        templateResult: function (data) {
          if (!data.newTag) return data.text;
          return $('<span class="kw-new"></span>').text("+ Add “" + data.text + "”");
        },
        language: {
          noResults: function () { return "Type a keyword, then press Enter"; }
        }
      });
    });
  }

  $(function () { start(document); });
  $(document).on("formset:added", function (e, row) { start(row || e.target); });
})(window.django && window.django.jQuery);
