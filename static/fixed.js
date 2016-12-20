function get(url, callback) {
  var xhr = new XMLHttpRequest();
  xhr.open("get", url);
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4 && xhr.status == 200) {
      callback(xhr.response);
    }
  }
  xhr.send();
}

function initFixedCounter() {
  var lang_code = document.documentElement.lang;
  var strings = document.getElementById("js-strings").dataset;
  var s = strings.refsAddedTodaySingular, p = strings.refsAddedTodayPlural;
  if (s && p)  {
    var url = lang_code + "/fixed";
    var container = document.getElementById("fixed-count-container");
    function render(fixed) {
      container.innerHTML = (parseInt(fixed) == 1 ? s : p).replace(
        "%s", '<span id="nfixed">' + fixed + '</span>');
      container.hidden = false;
    }
    get(url, render);
    setInterval(function() {
      get(url, render);
    }, 30000);
  }
}

if (document.readyState !== "loading") {
  initFixedCounter();
} else {
  window.addEventListener("DOMContentLoaded", function() {
    initFixedCounter();
  });
}
