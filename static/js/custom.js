// globals for debugging
var wizard = null;

// TODO: This is copied from category_filter.js :(
var customSpinner = new Spinner({
  scale: 0.5,
  top: 0,
  // Need this workaround for RTL
  // (https://github.com/fgnass/spin.js/issues/57)
  left: (document.dir === 'ltr') ? '100%' : '1%',
});

$(function() {
  function sendCreationRequest(payload) {
    return $.ajax({
      type: 'POST',
      url: wizard.getLangCode() + '/intersection',
      data: payload,
      dataType: 'JSON',
      contentType: 'application/json',
      timeout: 5 * 60 * 1000,
    });
  }

  var Card = {
    getId: function() {
      // Get the ID of this card.
      return null;
    },
    start: function(container) {
      // Put this card's HTML content inside a container.
    },
    end: function($container) {
      // Remove this card from a container.
    },
    // If set, callback for submiting data to the server. Should return a
    // Promise that resolves with the server response, or null upon validation
    // error.
    submit: null,
  };

  function LandingCard(wizard) {
    var id = 'custom-landing-card';
    this.getId = () => id;

    var $html = $('#' + id).detach();
    $html.find('#select-articles-link').click((e) => {
      e.preventDefault();
      wizard.advanceToCard('select-articles-card');
    });
    $html.find('#import-article-titles-link').click((e) => {
      e.preventDefault();
      wizard.advanceToCard('import-article-titles-card');
    });
    $html.find('#import-petscan-link').click((e) => {
      e.preventDefault();
      wizard.advanceToCard('import-petscan-card');
    });

    this.start = function($container) {
      $container.append($html);
    };

    this.end = function($container) {
      $html.detach();
    };
  }
  LandingCard.prototype = Card;

  function ImportArticlesCard(wizard) {
    var id = 'import-article-titles-card';
    this.getId = () => id;
    var $html = $('#' + id).detach();

    this.start = function($container) {
      $container.append($html);
      $html.find('textarea').focus();
    };

    this.end = function($container) {
      $html.detach();
    };

    this.submit = function() {
      var rawInput = $html.find('textarea').val();
      var payload = JSON.stringify({
        page_titles: rawInput.split(/\r?\n/g).map(title => title.trim()),
      });
      return sendCreationRequest(payload);
    };
  }
  ImportArticlesCard.prototype = Card;

  function ImportPetScanCard(wizard) {
    var id = 'import-petscan-card';
    this.getId = () => id;
    var $html = $('#' + id).detach();

    this.start = function($container) {
      $container.append($html);
      $html.find('input').focus();
    };

    this.end = function($container) {
      $html.detach();
    };

    this.submit = function() {
      var inputElem = $html.find('input')[0];
      var psid = extractPetScanID(inputElem.value);
      if ('setCustomValidity' in inputElem) {
        if (psid === null) {
          inputElem.setCustomValidity(
            wizard.getStrings().invalidPetscanInput);
          return null;
        }
        // Clear pre-existing errors.
        inputElem.setCustomValidity('');
      }
      var payload = JSON.stringify({
        psid: psid,
      });
      return sendCreationRequest(payload);
    }

    function extractPetScanID(input) {
      var psid = input.trim();
      var urlParser = document.createElement('a');
      urlParser.href = input;
      if (urlParser.hostname === 'petscan.wmflabs.org') {
        var searchParamsParser = new URLSearchParams(urlParser.search);
        psid = searchParamsParser.get('psid');
      }
      if (psid && psid.match(/^[0-9]+$/)) {
        return psid;
      }
      return null;
    };
  }
  ImportPetScanCard.prototype = Card;

  function SelectArticlesCard(wizard) {
    let id = 'select-articles-card';
    this.getId = () => id;
    let $html = $('#' + id).detach();
    let inputElement = $html.find('input').get(0);
    let articleSelector = null;

    this.start = function($container) {
      $container.append($html);
      inputElement.focus();
      articleSelector = new ArticleSelector(
        inputElement, $html.find('.spinner').get(0),
        $html.find('#selected-articles').get(0),
        $html.find('summary').get(0));
    };

    this.end = function($container) {
      articleSelector.removeEventListeners();
      $html.detach();
    };

    this.submit = function() {
      let pageIds = articleSelector.getSelectedArticles();
      if ('setCustomValidity' in inputElement) {
        if (pageIds.length === 0) {
          inputElement.setCustomValidity(
            wizard.getStrings().customNoArticlesSelected);
          return null;
        }
        // Clear pre-existing errors.
        inputElement.setCustomValidity('');
      }
      let payload = JSON.stringify({
        page_ids: pageIds,
      });
      return sendCreationRequest(payload);
    }
  }
  SelectArticlesCard.prototype = Card;

  function ProgressCard(wizard) {
    var self = this;
    var id = 'progress-card';
    this.getId = () => id;
    var $html = $('#' + id).detach();

    this.$inFlightRequest = null;

    this.start = function($container, $ajax, spinner) {
      if ($ajax === undefined) {
        // We're returning to this card from the final card, just pop ourselves
        // off the card stack.
        wizard.back();
        return;
      }
      $container.append($html);
      spinner.spin($html.find('.spinner')[0]);
      this.$inFlightRequest = $ajax;
      this.$inFlightRequest.always(function(response) {
        // When there's an error, the first argument is the XHR object.
        if (response === self.$inFlightRequest)  {
          if (response.statusText === 'abort') {
            // We canceled the request ourselves, nothing else to do.
            return;
          }
          response = null;
        }
        self.$inFlightRequest = null;
        if (response !== null && response['error'] === undefined
            && response['page_ids'].length > 0) {
          wizard.advanceToCard('custom-card-end', response);
        } else {
          wizard.advanceToCard('custom-card-failed');
        }
      });
    }

    this.end = function($container) {
      if (this.$inFlightRequest !== null) {
        this.$inFlightRequest.abort();
        this.$inFlightRequest = null;
      }
      $html.detach();
    };
  }
  ProgressCard.prototype = Card;

  function CreatedCard(wizard) {
    var id = 'custom-card-end';
    this.getId = () => id;
    var $html = $('#' + id).detach();

    this.start = function($container, response) {
      $container.append($html);
      $html.find('#custom-narticles').text(response.page_ids.length)
      var customURL = (
        document.location.origin + document.location.pathname +
        '?custom=' + response['id']);
      var l = $html.find('#custom-created-link')
      l.val(customURL);
      l.attr('size', customURL.length);
      l.focus();
      l[0].setSelectionRange(0, customURL.length);

      $html.find('#copy-link-text > a').attr('href', customURL);

      var strings = wizard.getStrings();
      if (!strings.customNumbers) return;
      $container.find('#custom-numbers').text(
        $.i18n(strings.customNumbers, response['page_ids'].length,
          response['ttl_days']));
    };

    this.end = function($container) {
      $html.detach();
    };
  }
  CreatedCard.prototype = Card;

  function FailedCard(wizard) {
    var id = 'custom-card-failed';
    this.getId = () => id;
    var $html = $('#' + id).detach();

    this.start = function($container, response) {
      $container.append($html);
    };

    this.end = function($container) {
      $html.detach();
    };
  }
  FailedCard.prototype = Card;

  function Wizard($container, $buttonBack, $buttonSubmit) {
    this._switchToCard = function(nextCardId, argsFromPrevious) {
      var nextCard = this.cards.filter((c) => c.getId() == nextCardId)[0];
      if (this._currentCard !== null) {
        this._currentCard.end(this.$container);
      }
      nextCard.start.apply(nextCard, [].concat(
        [this.$container], argsFromPrevious));
      this._currentCard = nextCard;
    }

    this._setUpButtons = function() {
      $buttonBack.hide();
      if (this._cardHistory.length)  {
        $buttonBack.show();
      }
      $buttonSubmit.hide();
      if (this._currentCard.submit !== null) {
        $buttonSubmit.show();
      }
    };

    // A Python-style "decorator" for making our public methods re-entrant, at
    // least as far as Cards are concerned. This allows, e.g., a card to call
    // back() while we're calling its start() from within back() without messing
    // up our internal state by deferring the inner back() call until the outer
    // has finished.
    var lock = 0;
    var r = (f) => {
      var self = this;
      var wrapped = function() {
        if (lock) {
          setTimeout(() => {
            wrapped.apply(self, arguments);
          }, 0);
          return;
        }
        lock = 1;
        f.apply(self, arguments);
        lock = 0;
      };
      return wrapped;
    };

    this.advanceToCard = r(function(nextCardId) {
      if (this._currentCard !== null) {
        this._cardHistory.push(this._currentCard);
      }
      this._switchToCard(nextCardId, [].slice.call(arguments, 1));
      this._setUpButtons();
    });

    this.landAtCard = r(function(cardId) {
      this._cardHistory = [];
      this._switchToCard(cardId);
      this._setUpButtons();
    });

    this.back = r(function() {
      var previousCard = this._cardHistory.pop();
      this._switchToCard(previousCard.getId());
      this._setUpButtons();
    })

    this.getLangCode = () => document.documentElement.dataset.chLangCode;
    this.getStrings = () => document.getElementById('js-strings').dataset;
    this.$container = $container;
    this.cards = [
      LandingCard,
      SelectArticlesCard,
      ImportArticlesCard,
      ImportPetScanCard,
      ProgressCard,
      CreatedCard,
      FailedCard,
    ].map((ctor) => new ctor(this), this);

    $buttonBack.click((e) => {
      e.preventDefault();
      this.back();
    });
    $buttonSubmit.click((e) => {
      e.preventDefault();
      var promise = this._currentCard.submit();
      if (promise !== null) {
        this.advanceToCard('progress-card', promise, customSpinner);
      }
    });

    this._cardHistory = [];
    this._currentCard = null;
  }

  wizard = new Wizard(
    $('#custom-card-container'),
    $('#custom-button-back'),
    $('#custom-button-submit'));
  wizard.landAtCard('custom-landing-card');
  $('#custom-modal-trigger').change(() => {
    wizard.landAtCard('custom-landing-card');
  });
  $('#custom-controls').removeAttr('hidden');
});
