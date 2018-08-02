const MAX_RESULTS = 400;
const SPINNER_START_DELAY_MS = 100;

// The tradeoff for this parameter is a little subtle.
// We're always making a mixture of local searches through the existing list
// of results in Awesomplete and remote searches in the server, so this
// parameter ultimately controls how we do the mixing.
// If SEARCH_THROTTLE_INTERVAL_MS is very low, we'll do a lot of queries to the
// server, and hardly ever do local searches, so overall this won't feel very
// responsive. If it's high, we'll do a lot of local searches, but if there are
// no results client-side, the user will need to wait longer for us to fetch
// results from the server, which can also feel unresponsive.
// We stay on the high side under the assumption that most users are not fast
// typists, so there will be plenty of time for performing server-side queries
// while they type search terms, but this is really just a magic number.
const SEARCH_THROTTLE_INTERVAL_MS = 800;

// http://stackoverflow.com/a/27078401
// Returns a function, that, when invoked, will only be triggered at most once
// during a given window of time. Normally, the throttled function will run
// as much as it can, without ever going more than once per `wait` duration;
// but if you'd like to disable the execution on the leading edge, pass
// `{leading: false}`. To disable execution on the trailing edge, ditto.
function throttle(func, wait, options) {
  var context, args, result;
  var timeout = null;
  var previous = 0;
  if (!options) options = {};
  var later = function() {
    previous = options.leading === false ? 0 : Date.now();
    timeout = null;
    result = func.apply(context, args);
    if (!timeout) context = args = null;
  };
  return function() {
    var now = Date.now();
    if (!previous && options.leading === false) previous = now;
    var remaining = wait - (now - previous);
    context = this;
    args = arguments;
    if (remaining <= 0 || remaining > wait) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      previous = now;
      result = func.apply(context, args);
      if (!timeout) context = args = null;
    } else if (!timeout && options.trailing !== false) {
      timeout = setTimeout(later, remaining);
    }
    return result;
  };
};

// globals for debugging
var awc = null;
var cf = null;

var spinner = new Spinner({
  scale: 0.5,
  // Need this workaround for RTL
  // (https://github.com/fgnass/spin.js/issues/57)
  left: (document.dir === 'ltr') ? '50%' : '80%',
  position: 'absolute',
});
spinner.spinning = false;

function CategoryFilter() {
  var self = this;
  var lang_code = document.documentElement.dataset.chLangCode;
  var strings = document.getElementById("js-strings").dataset;

  var cin = document.getElementById("category-input");
  var chi = document.getElementById("hidden-category-input");

  var xhr = null;
  var xhrCounter = 0;
  var xhrCompleted = 0;

  self._scheduleSpinnerStart = function(xhr) {
    // Whatever the final height of the input ends up being (which depends on
    // things we don't want to care about here, such as the font-size), make
    // sure the spinner appears next to it, vertically centered.
    var spi = document.getElementById('spinner');
    spi.style.height = cin.getBoundingClientRect().height + 'px';
    setTimeout(function() {
      if (spinner.spinning) return;
      if (xhr.readyState !== XMLHttpRequest.DONE) {
        spinner.spin(spi);
        spinner.spinning = true;
      }
    }, SPINNER_START_DELAY_MS);
  };

  self._buildSearchURL = function(q) {
    var url = lang_code + "/search/category?"
    // We trim() because that matches Awesomplete's behavior client-side.
    url += "q=" + encodeURIComponent(q.trim())
    url += "&max_results=" + MAX_RESULTS;
    return url;
  };

  self._forceSearch = function() {
    var timeout = null;
    var counter = ++xhrCounter;
    var url = self._buildSearchURL(cin.value);

    // Don't cancel the existing request: if a slightly older request returns
    // before this one does, we can still autocomplete in the client side.
    xhr = $.getJSON(url).done(function(response) {
      if (counter < xhrCompleted) {
          // We've already populated the list with the results of a more recent
          // query, so don't override it. This is a little uncommon, but could
          // happen if we end up racing cached and non-cached requests.
          return;
      }
      xhrCompleted = counter;
      awc.list = response['results'];
      awc.maxItems = response['results'].length;
      // We may have lost focus by the time the response arrives,
      // don't open the dropdown if that's the case.
      if (document.activeElement == cin) {
        awc.evaluate();
      }
    }).always(function() {
      // don't start the spinner after the request has returned,
      // and only stop the spinner when the last XHR returns,
      // in a chain of dropped requests.
      clearTimeout(timeout);
      if (xhrCounter == counter) {
        spinner.stop();
        spinner.spinning = false;
      }
    });
    timeout = self._scheduleSpinnerStart(xhr);
  }

  self._search = throttle(
    self._forceSearch, SEARCH_THROTTLE_INTERVAL_MS);

  // Functions that plug into Awesomplete

  function item(originalItem, suggestion, input) {
    var li;
    if (input) {
      li = originalItem(suggestion.label.title, input);
    } else {
      li = document.createElement("li");
      li.innerHTML = suggestion.label.title;
    }

    var ldiv = document.createElement('div');
    ldiv.innerHTML = li.innerHTML;
    ldiv.classList.add('label');

    var pdiv = document.createElement("div");
    var npages = suggestion.label.npages;
    if (strings.articleCount) {
      pdiv.innerText = $.i18n(strings.articleCount, npages);
    }
    pdiv.classList.add("npages");

    li.innerHTML = "";
    li.appendChild(ldiv);
    li.appendChild(pdiv);
    return li;
  }

  // Awesomplete allows us to have a `label` (the text that gets displayed in
  // the dropdown and matched against) and a `value` (the actual value that ends
  // up in the <input> when an option is selected) for each item.
  // We want the `label` to go into the <input>, but use the `value` to keep
  // track of the category id, so we need to override Awesomplete's `data` and
  // `replace` functions.
  function data(item, input) {
    return {label: {title: item.title, npages: item.npages}, value: item.id};
  }

  function filter(originalFilter, suggestion, value) {
    return originalFilter(suggestion.label.title, value);
  }

  function replace(suggestion) {
    this.input.value = suggestion.label.title;
  }

  function sort(sugg1, sugg2) {
    return sugg1.label.title.localeCompare(sugg2.label.title);
  }

  function setHiddenCategoryAndNextId(formElem, nextCategoryId) {
    var ihi = document.getElementById("hidden-id-input");
    if (ihi !== null && chi.value !== nextCategoryId) {
      formElem.removeChild(ihi);
    }
    chi.value = nextCategoryId;
  }

  // ...and now the actual Awesomplete integration:

  awc = new Awesomplete(cin);
  awc.minChars = 0; // open dropdown on focus
  awc.replace = replace;
  awc.data = data;
  awc.filter = filter.bind(null, awc.filter);
  awc.sort = sort;
  awc.item = item.bind(null, awc.item); // handle empty cin

  // Note that Awesomplete installs its own "input" handler that calls
  // evaluate(). We do want Awesomplete to evaluate locally sometimes,
  // so we don't bother working around that.
  cin.addEventListener("input", self._search);
  cin.addEventListener("click", function() {
    if (!cin.value.trim()) {
      self._search();  // populate dropdown if empty, then open
    } else {
      awc.evaluate();  // just open it
    }
  });

  cin.addEventListener("awesomplete-open", function() {
    this.classList.add("open");
  })

  cin.addEventListener("awesomplete-close", function() {
    if (cin.value === '') {
      setHiddenCategoryAndNextId(this.form, cin.value);
    }
    this.classList.remove("open");
  })

  cin.addEventListener("awesomplete-highlight", function() {
    if (!awc.selected) {
      return;
    }

    var listRect = awc.ul.getBoundingClientRect(),
        elemRect = awc.ul.children[awc.index].getBoundingClientRect(),
        offset = elemRect.top - listRect.top;
    awc.ul.scrollTop += offset;
  });

  cin.addEventListener("awesomplete-selectcomplete", function(obj) {
    setHiddenCategoryAndNextId(this.form, obj.text.value);
    this.form.submit();
  });

  cin.form.addEventListener("submit", function() {
    setHiddenCategoryAndNextId(this, chi.value);
    return true;
  });

  // We're ready, display the input!
  cin.form.hidden = false;
  if (cin.autofocus) {
    // Force autofocus, looks like it doesn't work on Chrome sometimes
    cin.focus();
  }
}

$(function() {
  cf = new CategoryFilter();
});
