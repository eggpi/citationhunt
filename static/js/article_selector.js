function ArticleSelector(inputElement, spinnerElement, selectionResultsOl,
                         previewElement) {
  let self = this;
  let langCode = document.documentElement.dataset.chLangCode;
  let langTag = document.documentElement.lang;
  let strings = document.getElementById("js-strings").dataset;

  function buildSearchURL(q) {
    var url = langCode + "/search/article?"
    // We trim() because that matches Awesomplete's behavior client-side.
    url += "q=" + encodeURIComponent(q.trim())
    url += "&max_results=" + MAX_RESULTS;
    return url;
  };

  function populateItemHTML(container, suggestion) {
    let ldiv = document.createElement('div');
    ldiv.innerHTML = container.innerHTML;
    ldiv.classList.add('label');

    let pdiv = document.createElement('div');
    let nsnippets = suggestion.label.snippets.length;
    if (strings.articleCount) {
      pdiv.innerText = $.i18n(strings.snippetCount, nsnippets);
    }
    pdiv.classList.add('count');

    if (self.getSelectedArticles().indexOf(suggestion.value) > -1) {
      container.classList.add('selected');
    }
    container.innerHTML = '';
    container.appendChild(ldiv);
    container.appendChild(pdiv);
  }

  let searchBar = new SearchBar(
    inputElement, spinnerElement, buildSearchURL, populateItemHTML);

  // Awesomplete allows us to have a `label` (the text that gets displayed in
  // the dropdown and matched against) and a `value` (the actual value that ends
  // up in the <input> when an option is selected) for each item.
  // We want the `label` to go into the <input>, but use the `value` to keep
  // track of the page id, so we need to override Awesomplete's `data` and
  // `replace` functions.
  function data(item, input) {
    return {label: {title: item.title, snippets: item.snippets},
            value: item.page_id};
  }
  searchBar.awesomplete.data = data;

  self.getSelectedArticles = function() {
    return Array.prototype.map.call(selectionResultsOl.querySelectorAll('li'),
      (li) => { return parseInt(li.getAttribute('data-pageid'), 10); });
  }

  self.removeEventListeners = function() {
    inputElement.removeEventListener('awesomplete-select', selectArticle);
    selectionResultsOl.removeEventListener('click', removeArticleOnPreviewClick);
    searchBar.awesomplete.destroy();
  }

  function updatePreviewSummary() {
    let articles = snippets = 0;
    Array.prototype.forEach.call(selectionResultsOl.querySelectorAll('li'),
      (li) => {
        articles++;
        snippets += parseInt(li.getAttribute('data-snippets'), 10);
      });
    previewElement.innerText = $.i18n(strings.selectArticlesSummary,
      articles, snippets);
  }

  function insertSelectedArticleSorted(li) {
    let insertionPointLi = null;
    // It's easier for the user to find articles in the list if they are sorted.
    for (let i = 0; i < selectionResultsOl.childNodes.length; i++) {
      let candidate = selectionResultsOl.childNodes[i];
      let cmp = li.lastChild.innerText.localeCompare(
        candidate.lastChild.innerText, langTag);
      if (cmp < 0) {
        insertionPointLi = candidate;
        break;
      }
    }
    selectionResultsOl.insertBefore(li, insertionPointLi);
  }

  function selectArticle(obj) {
    // Don't close the dialog
    obj.preventDefault();
    if (self.getSelectedArticles().indexOf(obj.text.value) > -1) {
      return;
    }
    let li = document.createElement('li');
    let rmButton = document.createElement('span');
    rmButton.classList.add('remove-button');
    li.appendChild(rmButton);
    let title = document.createElement('span');
    title.innerText = obj.text.label.title;
    li.appendChild(title);
    li.setAttribute('data-pageid', obj.text.value);
    li.setAttribute('data-snippets', obj.text.label.snippets.length);
    insertSelectedArticleSorted(li);
    // A bit overkill but we re-create the result elements to make sure that
    // the selected articles have the right CSS class.
    searchBar.awesomplete.evaluate();
    updatePreviewSummary(obj);
  }
  inputElement.addEventListener('awesomplete-select', selectArticle);

  function removeArticleOnPreviewClick(evt) {
    if (evt.target.classList.contains('remove-button')) {
      selectionResultsOl.removeChild(evt.target.parentNode);
      updatePreviewSummary();
    }
  }
  selectionResultsOl.addEventListener('click', removeArticleOnPreviewClick);

  updatePreviewSummary();
}
