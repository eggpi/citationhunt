function applyTheme(theme, options) {
  if ("localStorage" in window) {
    localStorage.setItem("theme", theme);
  }

  if (options && options.transition) {
    document.body.classList.add("interactive-theme-transition");
  }
  document.body.setAttribute("theme", theme);

  let toggle = document.getElementById("theme-toggle");
  if (!toggle) return;
  let strings = document.getElementById("js-strings").dataset;
  if (!strings) return;
  if (theme == "dark" && strings.darkTheme) {
    toggle.innerText = strings.defaultTheme;
  } else if (strings.defaultTheme) {
    toggle.innerText = strings.darkTheme;
  }
}

function toggleTheme() {
  let current = document.body.getAttribute("theme");
  if (!current) current = "default";
  applyTheme(current == "default" ? "dark" : "default", {transition: true});
}

function initThemeToggle() {
  if ("localStorage" in window) {
    let theme = localStorage.getItem("theme");
    applyTheme(theme ? theme : "default", {transition: false});
  }

  let toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", toggleTheme);
  }
}

if (document.readyState !== "loading") {
  initThemeToggle();
} else {
  window.addEventListener("DOMContentLoaded", function() {
    initThemeToggle();
  });
}
