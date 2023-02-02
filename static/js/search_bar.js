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

function makeSpinner(spinnerElement) {
  spinnerElement.innerHTML = '';
  return new Spinner({
    scale: 0.5,
    // Need this workaround for RTL
    // (https://github.com/fgnass/spin.js/issues/57)
    left: (document.dir === 'ltr') ? '50%' : '80%',
    position: 'absolute',
    color: getComputedStyle(spinnerElement).color,
  });
}

// http://stackoverflow.com/a/27078401
// Returns a function, that, when invoked, will only be triggered at most once
// during a given window of time. Normally, the throttled function will run
// as much as it can, without ever going more than once per `wait` duration;
// but if you'd like to disable the execution on the leading edge, pass
// `{leading: false}`. To disable execution on the trailing edge, ditto.
function throttle(func, wait, options) {
  let context, args, result;
  let timeout = null;
  let previous = 0;
  if (!options) options = {};
  let later = function() {
    previous = options.leading === false ? 0 : Date.now();
    timeout = null;
    result = func.apply(context, args);
    if (!timeout) context = args = null;
  };
  return function() {
    let now = Date.now();
    if (!previous && options.leading === false) previous = now;
    let remaining = wait - (now - previous);
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

function SearchBar(
    inputElement, spinnerElement,
    buildSearchURL, populateItemHTML) {
  let self = this;
  let ie = inputElement;  // shorthand
  let spinner = null;

  self._scheduleSpinnerStart = function(xhr) {
    // Whatever the final height of the input ends up being (which depends on
    // things we don't want to care about here, such as the font-size), make
    // sure the spinner appears next to it, vertically centered.
    spinnerElement.style.height = ie.getBoundingClientRect().height + 'px';
    spinnerElement.style.width = spinnerElement.style.height;
    return setTimeout(function() {
      if (spinner) return;
      spinner = makeSpinner(spinnerElement);
      if (xhr.readyState !== XMLHttpRequest.DONE) {
        spinner.spin(spinnerElement);
      }
    }, SPINNER_START_DELAY_MS);
  };

  let xhr = null;
  let xhrCounter = 0;
  let xhrCompleted = 0;

  self._forceSearch = function() {
    let timeout = null;
    let counter = ++xhrCounter;
    let url = buildSearchURL(ie.value);

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
      self.awesomplete.list = response['results'];
      self.awesomplete.maxItems = response['results'].length;
      // We may have lost focus by the time the response arrives,
      // don't open the dropdown if that's the case.
      if (document.activeElement == ie) {
        self.awesomplete.evaluate();
      }
    }).always(function() {
      // Don't start the spinner after the request has returned,
      // and only stop the spinner when the last XHR returns,
      // in a chain of dropped requests.
      clearTimeout(timeout);
      if (xhrCounter == counter) {
        spinner.stop();
        spinner = null;
      }
    });
    if (ie.value.length >= self.awesomplete.minChars) {
      timeout = self._scheduleSpinnerStart(xhr);
    }
  }

  self._search = throttle(
    self._forceSearch, SEARCH_THROTTLE_INTERVAL_MS);

  function filter(suggestion, value) {
    return Awesomplete.FILTER_CONTAINS(suggestion.label.title, value);
  }

  function replace(suggestion) {
    this.input.value = suggestion.label.title;
  }

  function sort(sugg1, sugg2) {
    return sugg1.label.title.localeCompare(sugg2.label.title,
      document.documentElement.lang);
  }

  function item(suggestion, input) {
    let li = Awesomplete.ITEM(suggestion.label.title, input);
    populateItemHTML(li, suggestion);
    return li;
  }

  // Note that Awesomplete installs its own "input" handler that calls
  // evaluate(). We do want Awesomplete to evaluate locally sometimes,
  // so we don't bother working around that.
  inputElement.addEventListener('input', self._search);
  inputElement.addEventListener('click', self._search);

  function scrollToSelectedItem() {
    if (!self.awesomplete.selected) {
      return;
    }
    let ul = self.awesomplete.ul;
    let listRect = ul.getBoundingClientRect(),
        elemRect = ul.children[self.awesomplete.index].getBoundingClientRect(),
        offset = elemRect.top - listRect.top;
    ul.scrollTop += offset;
  }
  ie.addEventListener('awesomplete-highlight', scrollToSelectedItem);

  self.removeEventListeners = function() {
    ie.removeEventListener('input', self._search);
    ie.removeEventListener('click', self._search);
    ie.removeEventListener('awesomplete-highlight', scrollToSelectedItem);
  }

  self.awesomplete = new Awesomplete(ie, {
    minChars: 1,
    data: null,  // needs to be overriden by user
    filter: filter,
    replace: replace,
    sort: sort,
    item: item
  });
}
