(function () {
  const wrap = document.querySelector("[data-url-open]");
  const input = wrap && wrap.querySelector("input");
  if (!wrap || !input) return;

  function hrefFor(url) {
    const raw = (url || "").trim();
    if (!raw || /[\u0000-\u001F\u007F]/.test(raw)) return "";
    if (/^(javascript|data|vbscript|file):/i.test(raw)) return "";
    try {
      const withProtocol = /^https?:\/\//i.test(raw) ? raw : "https://" + raw;
      const parsed = new URL(withProtocol);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return "";
      if (parsed.username || parsed.password) return "";
      if (!parsed.hostname) return "";
      return parsed.href;
    } catch {
      return "";
    }
  }

  let hovered = false;
  let modifier = false;

  function sync() {
    const href = hrefFor(input.value);
    const clickable = Boolean(href && hovered && modifier);
    wrap.classList.toggle("is-clickable", clickable);
    wrap.title = href
      ? "Hold Ctrl (⌘ on Mac) while hovering, then click to open in a new tab"
      : "";
  }

  function onKey(event) {
    modifier = event.ctrlKey || event.metaKey;
    sync();
  }

  wrap.addEventListener("mouseenter", function () {
    hovered = true;
    sync();
  });
  wrap.addEventListener("mouseleave", function () {
    hovered = false;
    sync();
  });
  window.addEventListener("keydown", onKey);
  window.addEventListener("keyup", onKey);
  window.addEventListener("blur", function () {
    modifier = false;
    sync();
  });
  input.addEventListener("input", sync);

  function openIfModifier(event) {
    if (!(event.ctrlKey || event.metaKey)) return;
    const href = hrefFor(input.value);
    if (!href) return;
    event.preventDefault();
    window.open(href, "_blank", "noopener,noreferrer");
  }

  wrap.addEventListener("click", openIfModifier);
  wrap.addEventListener("contextmenu", openIfModifier);
})();
