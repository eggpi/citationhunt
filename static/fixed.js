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
  if (!s || !p)  {
      return;
  }

  var baseUrl = lang_code + "/fixed";
  var container = document.getElementById("fixed-count-container");

  // Find the Unix timestamp of today at midnight (in the local timezone)
  function today() {
    return (new Date()).setHours(0, 0, 0, 0) / 1000;
  }

  function render(fixed) {
    fixed = parseInt(fixed);
    container.innerHTML = (fixed == 1 ? s : p).replace(
      "%s", '<span id="nfixed">' + fixed + '</span>');
    container.hidden = (fixed <= 0);
  }

  function update() {
    var url = baseUrl + '?from_ts=' + today();
    get(url, render);
  }

  update();
  setInterval(function() {
    update();
  }, 45000);
}

if (document.readyState !== "loading") {
  initFixedCounter();
} else {
  window.addEventListener("DOMContentLoaded", function() {
    initFixedCounter();
  });
}
