let cf;  // for debugging

function initCategoryFilter() {
  cf = new CategoryFilter();
}

function CategoryFilter() {
  let self = this;
  let lang_code = document.documentElement.dataset.chLangCode;
  let strings = document.getElementById("js-strings").dataset;

  let cin = document.getElementById("category-input");
  let chi = document.getElementById("hidden-category-input");

  function buildSearchURL(q) {
    let url = lang_code + "/search/category?"
    // We trim() because that matches Awesomplete's behavior client-side.
    url += "q=" + encodeURIComponent(q.trim())
    url += "&max_results=" + MAX_RESULTS;
    return url;
  };

  function populateItemHTML(container, suggestion) {
    let ldiv = document.createElement('div');
    ldiv.innerHTML = container.innerHTML;
    ldiv.classList.add('label');

    let pdiv = document.createElement("div");
    let npages = suggestion.label.npages;
    if (strings.articleCount) {
      pdiv.innerText = $.i18n(strings.articleCount, npages);
    }
    pdiv.classList.add("count");

    container.innerHTML = '';
    container.appendChild(ldiv);
    container.appendChild(pdiv);
  }

  function confirmBeforeLeavingCustom(nextCategoryId) {
    let customhi = document.getElementById("hidden-custom-input");
    let leaving = true;
    if (customhi !== null && nextCategoryId != 'all') {
      if (customhi.value) {
        leaving = window.confirm(strings.leavingCustom);
      }
      if (leaving) {
        // Disable the hidden input so we don't end up with a &custom= in the
        // URL. This is purely for cosmetic reasons as the backend gives
        // precedence to a category id if it's present. We want to disable
        // not remove because removing breaks the back button.
        customhi.disabled = true;
      }
    }
    return leaving;
  }

  function setHiddenCategoryAndNextId(formElem, nextCategoryId) {
    let ihi = document.getElementById("hidden-id-input");
    if (ihi !== null && chi.value !== nextCategoryId) {
      formElem.removeChild(ihi);
    }
    chi.value = nextCategoryId;
    chi.disabled = (nextCategoryId == 'all');
  }

  self.searchBar = new SearchBar(
    cin, document.getElementById('category-filter-spinner'),
    buildSearchURL, populateItemHTML);

  // Awesomplete allows us to have a `label` (the text that gets displayed in
  // the dropdown and matched against) and a `value` (the actual value that ends
  // up in the <input> when an option is selected) for each item.
  // We want the `label` to go into the <input>, but use the `value` to keep
  // track of the category id, so we need to override Awesomplete's `data` and
  // `replace` functions.
  function data(item, input) {
    return {label: {title: item.title, npages: item.npages}, value: item.id};
  }

  self.searchBar.awesomplete.data = data;

  cin.addEventListener("awesomplete-close", function() {
    if (cin.value === '') {
      setHiddenCategoryAndNextId(this.form, 'all');
    }
  })

  cin.addEventListener("awesomplete-selectcomplete", function(obj) {
    if (!confirmBeforeLeavingCustom(obj.text.value)) {
      cin.value = '';
      return;
    }
    setHiddenCategoryAndNextId(this.form, obj.text.value);
    this.form.submit();
  });

  cin.form.addEventListener("submit", function(e) {
    if (!confirmBeforeLeavingCustom(chi.value)) {
      e.preventDefault();
    }
    setHiddenCategoryAndNextId(this, chi.value);
  });

  // We're ready, display the input!
  cin.form.hidden = false;
  if (cin.autofocus) {
    // Force autofocus, looks like it doesn't work on Chrome sometimes
    cin.focus();
  }
}

if (document.readyState !== "loading") {
  initCategoryFilter();
} else {
  window.addEventListener("DOMContentLoaded", initCategoryFilter);
}
