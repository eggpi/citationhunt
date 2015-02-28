function initCategoryFilter() {
  var cin = document.getElementById("category-input");
  var chi = document.getElementById("hidden-category-input");
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

  function setHiddenCategory() {
    var catname = cin.value.toLocaleLowerCase();

    chi.value = "all";
    for (var i = 0; i < options.length; i++) {
      if (options[i].label.toLocaleLowerCase() == catname) {
        chi.value = options[i].value;
      }
    }
  }

  cin.addEventListener("awesomplete-selectcomplete", function() {
    setHiddenCategory();
    this.form.submit();
  });

  cin.form.addEventListener("submit", function() {
    setHiddenCategory();
    return true;
  });

  cin.style.visibility = '';
}

function loadCategoriesAndFilter() {
  var iframe = document.createElement("iframe");
  iframe.src = "/categories.html";
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
