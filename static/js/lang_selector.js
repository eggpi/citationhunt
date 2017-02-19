function initLangSelector() {
  var lang_selector = document.getElementById('lang-selector');
  lang_selector.addEventListener('change', function() {
    for (var i = 0; i < lang_selector.options.length; i++) {
      var op = this.options[i];
      if (op.selected) {
        window.location = op.getAttribute('data-lang-code');
      }
    }
  });
}

if (document.readyState !== "loading") {
  initLangSelector();
} else {
  window.addEventListener("DOMContentLoaded", function() {
    initLangSelector();
  });
}
