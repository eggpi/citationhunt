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
  var lang_code = document.documentElement.dataset.chLangCode;
  var strings = document.getElementById("js-strings").dataset;
  if (!strings.refsAddedToday) return;

  var baseUrl = lang_code + "/fixed";
  var $container = $("#fixed-count-container");

  // Find the Unix timestamp of today at midnight (in the local timezone)
  function today() {
    return (new Date()).setHours(0, 0, 0, 0) / 1000;
  }

  function render(fixed) {
    fixed = parseInt(fixed);
    // First pass the bare number to $.i18n so it can compute the correct plural
    // form, then replace it with the actual markup we want in the result.
    var markup = '<span id="nfixed">' + fixed + "</span>";
    $container.html(
        $.i18n(strings.refsAddedToday, fixed).replace(fixed, markup));
    if (fixed) $container.removeAttr('hidden');
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

$(initFixedCounter);
