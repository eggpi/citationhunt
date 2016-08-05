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

  function item(originalItem, text, input) {
    if (input) {
      return originalItem(text, input);
    }

    var li = document.createElement("li");
    li.innerHTML = text;
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
    return {label: item.title, value: item.id};
  }

  function replace(text) {
    this.input.value = text.label;
  }

  var awc = new Awesomplete(cin);
  awc.minChars = 0; // open dropdown on focus
  awc.replace = replace;
  awc.data = data;
  awc.sort = undefined; // sort alphabetially regardless of item length
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

if (document.readyState !== "loading") {
  initCategoryFilter();
} else {
  window.addEventListener("DOMContentLoaded", function() {
    initCategoryFilter();
  });
}
