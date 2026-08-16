(function () {
  const article = document.querySelector(".cv");
  if (!article) return;
  const jobId = article.getAttribute("data-job-id");
  if (!jobId) return;

  const toolbar = document.createElement("div");
  toolbar.className = "cv-fmt";
  toolbar.hidden = true;
  toolbar.innerHTML =
    '<button type="button" data-cmd="bold" title="Bold"><b>B</b></button>' +
    '<button type="button" data-cmd="italic" title="Italic"><i>I</i></button>';
  document.body.appendChild(toolbar);

  let active = null;
  let suppressBlur = false;

  function placeToolbar(el) {
    const rect = el.getBoundingClientRect();
    toolbar.hidden = false;
    toolbar.style.top = `${window.scrollY + rect.top - toolbar.offsetHeight - 6}px`;
    toolbar.style.left = `${window.scrollX + rect.left}px`;
  }

  function hideToolbar() {
    toolbar.hidden = true;
  }

  function format(cmd) {
    if (!active) return;
    active.focus();
    document.execCommand(cmd, false, null);
    syncButtons();
  }

  function syncButtons() {
    toolbar.querySelectorAll("button[data-cmd]").forEach((button) => {
      button.classList.toggle("on", document.queryCommandState(button.getAttribute("data-cmd")));
    });
  }

  toolbar.addEventListener("mousedown", (event) => {
    event.preventDefault();
    suppressBlur = true;
  });
  toolbar.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-cmd]");
    if (button) format(button.getAttribute("data-cmd"));
    suppressBlur = false;
  });

  article.addEventListener("click", (event) => {
    const item = event.target.closest("[data-path]");
    if (!item || !article.contains(item)) return;
    if (active === item) return;
    if (active) active.blur();
    active = item;
    item.setAttribute("contenteditable", "true");
    item.classList.add("is-editing");
    item.focus();
    placeToolbar(item);
    syncButtons();
  });

  article.addEventListener("keyup", () => {
    if (active) {
      placeToolbar(active);
      syncButtons();
    }
  });

  article.addEventListener("keydown", (event) => {
    if (!active) return;
    if (event.key === "Enter") {
      event.preventDefault();
      if (active.classList.contains("intro")) {
        document.execCommand("insertLineBreak", false, null);
        return;
      }
      active.blur();
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "b") {
      event.preventDefault();
      format("bold");
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "i") {
      event.preventDefault();
      format("italic");
    }
  });

  article.addEventListener("paste", (event) => {
    if (!active) return;
    event.preventDefault();
    const text = (event.clipboardData || window.clipboardData).getData("text/plain");
    document.execCommand("insertText", false, text);
  });

  document.addEventListener("focusin", (event) => {
    if (toolbar.contains(event.target)) return;
    if (active && event.target !== active && !active.contains(event.target)) {
      active.blur();
    }
  });

  article.addEventListener(
    "blur",
    (event) => {
      const item = event.target.closest("[data-path]");
      if (!item) return;
      if (suppressBlur) {
        suppressBlur = false;
        return;
      }
      item.removeAttribute("contenteditable");
      item.classList.remove("is-editing");
      if (active === item) active = null;
      hideToolbar();
      const path = item.getAttribute("data-path");
      const html = item.innerHTML;
      fetch(`/jobs/${jobId}/cv-bullet`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ path, html }),
      })
        .then((response) => {
          if (!response.ok) throw new Error("save failed");
          return response.json();
        })
        .then((data) => {
          if (data.html !== undefined) item.innerHTML = data.html;
          item.classList.add("is-saved");
          setTimeout(() => item.classList.remove("is-saved"), 700);
        })
        .catch(() => {
          item.classList.add("is-error");
          setTimeout(() => item.classList.remove("is-error"), 1200);
        });
    },
    true
  );
})();
