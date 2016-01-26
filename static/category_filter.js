function initCategoryFilter() {
  var cin = document.getElementById("category-input");
  var chi = document.getElementById("hidden-category-input");
  var ihi = document.getElementById("hidden-id-input");
  var options = document.getElementsByTagName("option");

  function item(originalItem, text, input) {
    if (input) {
      return originalItem(text, input);
    }

    var li = document.createElement("li");
    li.innerHTML = text;
    return li;
  }

  var awc = new Awesomplete(cin);
  awc.minChars = 0; // open dropdown on focus
  awc.maxItems = options.length; // display all options when cin is empty
  awc.sort = undefined; // sort alphabetially regardless of item length
  awc.item = item.bind(null, awc.item); // handle empty cin

  cin.addEventListener("click", function() {
    awc.evaluate();
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

  function setHiddenCategoryAndNextId(formElem) {
    var catname = cin.value.toLocaleLowerCase();
    var currentCategoryId = chi.value;

    chi.value = "all";
    for (var i = 0; i < options.length; i++) {
      if (options[i].label.toLocaleLowerCase() == catname) {
        chi.value = options[i].value;
      }
    }

    if (chi.value !== currentCategoryId) {
      formElem.removeChild(ihi);
    }
  }

  cin.addEventListener("awesomplete-selectcomplete", function() {
    setHiddenCategoryAndNextId(this.form);
    this.form.submit();
  });

  cin.form.addEventListener("submit", function() {
    setHiddenCategoryAndNextId(this.form);
    return true;
  });

  cin.style.visibility = '';
  if (cin.autofocus) {
    // Force autofocus, looks like it doesn't work on Chrome sometimes
    cin.focus();
  }
}

function loadCategoriesAndFilter() {
  var lang_code = document.documentElement.lang;
  var iframe = document.createElement("iframe");
  iframe.src = lang_code + "/categories.html";
  iframe.hidden = true;
  iframe.addEventListener("load", function() {
    var catlist = iframe.contentDocument.getElementById("categories");
    document.body.appendChild(catlist);

    if (document.readyState !== "loading") {
      initCategoryFilter();
    } else {
      window.addEventListener("DOMContentLoaded", function() {
        initCategoryFilter();
      });
    }
  });

  document.body.appendChild(iframe);
}

loadCategoriesAndFilter();
