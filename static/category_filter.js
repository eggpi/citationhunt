function initCategoryFilter() {
  var cin = document.getElementById("category-input");
  var chi = document.getElementById("hidden-category-input");
  var options = document.getElementsByTagName("option");

  var currentCategoryId = chi.value;
  for (var i = 0; i < options.length; i++) {
    if (options[i].value === currentCategoryId) {
      cin.value = options[i].label;
      chi.value = options[i].value;
    }
  }

  function filterEmptyMatchesAll(text, input) {
    return (input === "") || Awesomplete.FILTER_CONTAINS(text, input);
  }

  var awc = new Awesomplete(cin);
  awc.minChars = 0;
  awc.maxItems = options.length;
  awc.sort = undefined;

  cin.addEventListener('click', function() {
    awc.evaluate();
  });

  cin.addEventListener("awesomplete-open", function() {
    this.classList.add("open");
  })

  cin.addEventListener("awesomplete-close", function() {
    this.classList.remove("open");
  })

  function set_hidden_category() {
    var catname = cin.value.toLocaleLowerCase();

    chi.value = "all";
    for (var i = 0; i < options.length; i++) {
      if (options[i].label.toLocaleLowerCase() == catname) {
        chi.value = options[i].value;
      }
    }
  }

  cin.addEventListener("awesomplete-selectcomplete", function() {
    set_hidden_category();
    this.form.submit();
  });

  cin.form.addEventListener("submit", function() {
    set_hidden_category();
    return true;
  });

  cin.style.visibility = '';
}

var iframe = document.getElementById("categories-iframe");
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
