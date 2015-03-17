function reportEvent(evt) {
  if ('sendBeacon' in navigator) {
    var data = JSON.stringify({'event': evt});
    var url = 'stats' + window.location.search;
    navigator.sendBeacon(url, data);
  }
}

function reportOnDOMEvent(elementId, DOMEvent, evt) {
  var e = document.getElementById(elementId);
  e.addEventListener(DOMEvent, reportEvent.bind(null, evt));
}

function initStats() {
  reportOnDOMEvent('button-next', 'click', 'next-click');
  reportOnDOMEvent('button-wikilink', 'click', 'yes-click');
  reportOnDOMEvent('article-link', 'click', 'article-click');
}

if (document.readyState !== "loading") {
  initStats();
} else {
  window.addEventListener("DOMContentLoaded", function() {
    initStats();
  });
}
