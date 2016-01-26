var translatables = [
  {
    elementId: "intro",
    getContent: element => element.textContent.trim(),
    setContent: (element, text) => {
      element.textContent = text;
    },
  },
  {
    elementId: "github-link",
    getContent: element => element.textContent,
    setContent: (element, text) => {
      element.textContent = text;
    },
  },
  {
    elementId: "page-title-text",
    getContent: element => element.textContent,
    setContent: (element, text) => {
      element.textContent = text;
    },
  },
  {
    elementId: "category-input",
    getContent: element => element.placeholder,
    setContent: (element, text) => {
      element.placeholder = text;
    },
  },
  {
    elementId: "beginners-link-text",
    getContent: element => element.textContent,
    setContent: (element, text) => {
      element.textContent = text;
    },
  },
  {
    elementId: "button-wikilink",
    getContent: element => element.textContent,
    setContent: (element, text) => {
      element.textContent = text;
    },
  },
  {
    elementId: "button-next",
    getContent: element => element.textContent,
    setContent: (element, text) => {
      element.textContent = text;
    },
  },
  {
    elementId: "lead-hint",
    getContent: element => element.textContent,
    setContent: (element, text) => {
      element.textContent = text;
    },
  },
];

function sendResults(redirect) {
  var results = {};
  for (var tidx = 0; tidx < translatables.length; tidx++) {
    var obj = translatables[tidx];
    var element = document.getElementById(obj.elementId);
    if (obj.getContent(element) != obj.originalContent) {
      results[obj.elementId] = obj.getContent(element);
    }
  }

  if (!Object.keys(results).length) {
    if (redirect) location.href = "en";
    return;
  }

  var xhr = new XMLHttpRequest(false);
  xhr.open("POST", document.documentElement.lang + "/translation");
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(JSON.stringify(results));
  xhr.onload = () => {
    if (xhr.readyState === 4 && redirect) {
      location.href = "en";
    }
  }
}

function translationWizard() {
  var translate = document.getElementById("translate");
  var translate_box = document.getElementById("translate-box");
  translate_box.addEventListener("input", function() {
    obj.setContent(clone, translate_box.value);
  });

  var tidx = 0;
  var obj = null;
  var original = null, clone = null;

  for (tidx = 0; tidx < translatables.length; tidx++) {
    // first, save the original contents of each element so
    // we can know later whether they've changed
    var el = document.getElementById(translatables[tidx].elementId);
    translatables[tidx].originalContent = translatables[tidx].getContent(el);
  }
  tidx = 0;

  function highlightForTranslation() {
    if (clone != null) {
      obj.setContent(original, obj.getContent(clone));
      clone.parentNode.replaceChild(original, clone);
    }

    obj = translatables[tidx];
    original = document.getElementById(obj.elementId);
    clone = original.cloneNode(true);
    clone.style["z-index"] = 1;
    if (window.getComputedStyle(original).position === "static") {
      // The element needs to have a position so z-index applies
      clone.style["position"] = "relative";
    }
    clone.style["box-shadow"] = "0px 0px 15px white";

    original.parentNode.replaceChild(clone, original);
    translate_box.value = obj.getContent(clone);

    // move the translation box next to the clone
    var cloneRect = clone.getBoundingClientRect();
    var bodyRect = document.body.getBoundingClientRect();

    translate.style.top = "";
    translate.style.right = translate.style.left = "";

    var offset = (cloneRect.left > bodyRect.right / 2) ? -bodyRect.right + 30 : 30;
    var corner = (cloneRect.left > bodyRect.right / 2) ? "right" : "left";
    translate.style.top = (cloneRect.bottom | 0) + 15 + "px";
    translate.style[corner] = Math.abs((cloneRect.left | 0) + offset) + "px";
    translate_box.select();
  }

  var next = document.getElementById("translate-next");
  var prev = document.getElementById("translate-prev");

  next.addEventListener("click", () => {
    var done = (tidx === translatables.length -1);
    sendResults(done);
    if (done) return;
    if (tidx === translatables.length - 2) {
      next.textContent = "✔";
    }
    tidx++;
    prev.style.display = "inline";
    highlightForTranslation();
  });

  prev.addEventListener("click", () => {
    next.textContent = "➜";
    if (tidx === 0) {
      return;
    } else if (tidx === 1) {
      prev.style.display = "none";
    }
    tidx--;
    highlightForTranslation();
  });

  highlightForTranslation();
}

if (document.readyState !== "loading") {
  translationWizard();
} else {
  window.addEventListener("DOMContentLoaded", function() {
    translationWizard();
  });
}
