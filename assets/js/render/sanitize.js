/* Anything a visitor submits is rendered without raw HTML and then passed through here. The site shares its origin with the other
   pages of the organisation, so nothing from a submitted RFC may run code, load a script or reach another page's data.
   Needs window.DOMPurify (assets/vendor/purify.min.js). */

const TAGS = ["a", "b", "strong", "i", "em", "br", "hr", "p", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "code", "pre",
  "table", "thead", "tbody", "tr", "th", "td", "div", "span", "section", "figure", "figcaption", "button", "img", "dl", "dt", "dd",
  "sup", "sub", "del", "s"];
const ATTRS = ["id", "class", "href", "src", "alt", "title", "type", "data-copy", "colspan", "rowspan", "align", "rel", "target", "loading", "referrerpolicy"];
const ID_OK = /^(?:pt|en|zh)-[a-z0-9][a-z0-9-]*$/;

let ready = false;
function setup() {
  if (ready) return;
  ready = true;
  window.DOMPurify.addHook("afterSanitizeAttributes", node => {
    if (node.hasAttribute && node.hasAttribute("id") && !ID_OK.test(node.getAttribute("id"))) node.removeAttribute("id");   // no DOM clobbering
    if (node.tagName === "A") {
      const href = node.getAttribute("href") || "";
      if (/^https?:/i.test(href)) { node.setAttribute("target", "_blank"); node.setAttribute("rel", "noopener noreferrer"); }
    }
    if (node.tagName === "IMG") {
      if (!/^https:\/\//i.test(node.getAttribute("src") || "")) node.remove();       // https images only
      else { node.setAttribute("loading", "lazy"); node.setAttribute("referrerpolicy", "no-referrer"); }
    }
    if (node.tagName === "BUTTON" && !(node.hasAttribute("data-copy") && node.classList.contains("copy"))) node.remove();   // only the code figure's copy button
  });
}

export function sanitize(html) {
  if (!window.DOMPurify) throw new Error("DOMPurify is not loaded");
  setup();
  return window.DOMPurify.sanitize(html, {
    ALLOWED_TAGS: TAGS, ALLOWED_ATTR: ATTRS, ALLOW_DATA_ATTR: false, KEEP_CONTENT: true,   // ids are limited by the hook above, so names cannot clobber globals
    ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|#)/i
  });
}
