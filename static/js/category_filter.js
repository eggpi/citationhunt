// global for debugging
var awc = null;

// http://stackoverflow.com/a/8079681
function getScrollBarWidth () {
  var inner = document.createElement('p');
  inner.style.width = "100%";
  inner.style.height = "200px";

  var outer = document.createElement('div');
  outer.style.position = "absolute";
  outer.style.top = "0px";
  outer.style.left = "0px";
  outer.style.visibility = "hidden";
  outer.style.width = "200px";
  outer.style.height = "150px";
  outer.style.overflow = "hidden";
  outer.appendChild(inner);

  document.body.appendChild(outer);
  var w1 = inner.offsetWidth;
  outer.style.overflow = 'scroll';
  var w2 = inner.offsetWidth;
  if (w1 == w2) w2 = outer.clientWidth;
  document.body.removeChild(outer);

  return w1 - w2;
};

function getJSON(url, success, error) {
  var xhr = new XMLHttpRequest();
  xhr.open("get", url, true);
  xhr.responseType = "json";
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4 && xhr.status == 200) {
      success(xhr.response);
    } else {
      error && error(xhr);
    }
  };
  xhr.send();
}

function initCategoryFilter() {
  var cin = document.getElementById("category-input");
  var chi = document.getElementById("hidden-category-input");
  var ihi = document.getElementById("hidden-id-input");
  var strings = document.getElementById("js-strings").dataset;
  var scrollBarWidth = getScrollBarWidth();

  function search() {
    var lang_code = document.documentElement.lang;
    var url = lang_code + "/search/category?q=" + encodeURIComponent(cin.value);
    getJSON(url, function(response) {
      awc.list = response['results'];
      awc.maxItems = response['results'].length;
      awc.evaluate();
    }, function() {
      // What here?
    });
  }

  function item(originalItem, suggestion, input) {
    var li;
    if (input) {
      li = originalItem(suggestion.label.title, input);
    } else {
      li = document.createElement("li");
      li.innerHTML = suggestion.label.title;
    }

    var ldiv = document.createElement("div");
    ldiv.innerHTML = li.innerHTML;
    ldiv.classList.add('label');

    var pdiv = document.createElement("div");
    var npages = suggestion.label.npages;
    if (strings.articleCount) {
      pdiv.innerText = $.i18n(strings.articleCount, npages);
      if (document.dir === 'rtl') {
        pdiv.style.paddingLeft = scrollBarWidth + 'px';
      } else {
        pdiv.style.paddingRight = scrollBarWidth + 'px';
      }
    }
    pdiv.classList.add("npages");

    li.innerHTML = "";
    li.appendChild(ldiv);
    li.appendChild(pdiv);
    return li;
  }

  cin.addEventListener("input", search);

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

  awc = new Awesomplete(cin);
  awc.minChars = 0; // open dropdown on focus
  awc.replace = replace;
  awc.data = data;
  awc.filter = filter.bind(null, awc.filter);
  awc.sort = sort;
  awc.item = item.bind(null, awc.item); // handle empty cin

  cin.addEventListener("click", function() {
    search();
  });

  cin.addEventListener("awesomplete-open", function() {
    this.classList.add("open");
  })

  cin.addEventListener("awesomplete-close", function() {
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

  function setHiddenCategoryAndNextId(formElem, nextCategoryId) {
    if (chi.value !== nextCategoryId) {
      formElem.removeChild(ihi);
    }
    chi.value = nextCategoryId;
  }

  cin.addEventListener("awesomplete-selectcomplete", function(obj) {
    setHiddenCategoryAndNextId(this.form, obj.text.value);
    this.form.submit();
  });

  cin.form.addEventListener("submit", function() {
    setHiddenCategoryAndNextId(this, chi.value);
    return true;
  });

  cin.style.visibility = '';
  if (cin.autofocus) {
    // Force autofocus, looks like it doesn't work on Chrome sometimes
    cin.focus();
  }
}

$(initCategoryFilter);
