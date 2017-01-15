// key code -> action
// Make sure these match the tooltips set in initKeyboardShortcuts
var shortcuts = {
  "KeyG": function() {
    document.getElementById("button-wikilink").click();
  },
  "KeyN": function() {
    document.getElementById("button-next").click();
  }
};

function initKeyboardShortcuts() {
  document.body.addEventListener("keydown", function(evt) {
    if (evt.target != this) return;
    // Make sure we don't conflict with Ctrl+ shortcuts
    if ('getModifierState' in evt && evt.getModifierState("Control")) return;
    var key = evt.code;
    if (!key) key = "Key" + String.fromCharCode(evt.keyCode).toUpperCase();
    var handler = shortcuts[key];
    if (handler) handler();
  });

  var strings = document.getElementById("js-strings").dataset;
  if (strings.keyboardShortcut) {
    document.getElementById("button-wikilink").title = (
      strings.keyboardShortcut.replace("%s", "g"));
    document.getElementById("button-next").title = (
      strings.keyboardShortcut.replace("%s", "n"));
  }
}

if (document.readyState !== "loading") {
  initKeyboardShortcuts();
} else {
  window.addEventListener("DOMContentLoaded", function() {
    initKeyboardShortcuts();
  });
}
