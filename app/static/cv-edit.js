(function () {
  if (window.__cvEditReady) return;
  window.__cvEditReady = true;

  const roots = document.querySelectorAll(".cv[data-job-id], .letter[data-job-id], .shokumu[data-job-id]");
  if (!roots.length) return;

  const toolbar = document.createElement("div");
  toolbar.className = "cv-fmt";
  toolbar.hidden = true;
  toolbar.innerHTML =
    '<button type="button" data-cmd="bold" title="Bold"><b>B</b></button>' +
    '<button type="button" data-cmd="italic" title="Italic"><i>I</i></button>';
  document.body.appendChild(toolbar);

  let active = null;
  let suppressBlur = false;

  function jobIdFor(el) {
    const root = el.closest("[data-job-id]");
    return root ? root.getAttribute("data-job-id") : null;
  }

  function allowsLineBreak(el) {
    return el.classList.contains("intro") || el.classList.contains("letter-edit");
  }

  function isContactPath(path) {
    return path === "contact.full_name" || path === "contact.email" || path === "name";
  }

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

  function reindexList(section) {
    const prefix = section.getAttribute("data-cv-list");
    if (!prefix) return;
    section.querySelectorAll("[data-delete]").forEach((el, index) => {
      el.setAttribute("data-delete", `${prefix}.${index}`);
      const edit = el.querySelector("[data-path]");
      if (edit) edit.setAttribute("data-path", `${prefix}.${index}`);
    });
  }

  function deleteItem(item) {
    const path = item.getAttribute("data-delete");
    const jobId = jobIdFor(item);
    if (!path || !jobId || item.dataset.deleting) return;
    item.dataset.deleting = "1";
    const section = item.closest("[data-cv-list]");
    fetch(`/jobs/${jobId}/cv-bullet`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ path, html: "", delete: true }),
    })
      .then((response) => {
        if (!response.ok) throw new Error("delete failed");
        return response.json();
      })
      .then(() => {
        if (active && item.contains(active)) {
          active = null;
          hideToolbar();
        }
        item.remove();
        if (!section) return;
        reindexList(section);
        if (!section.querySelector("[data-delete]")) section.remove();
      })
      .catch(() => {
        delete item.dataset.deleting;
        item.classList.add("is-error");
        setTimeout(() => item.classList.remove("is-error"), 1200);
      });
  }

  function onRemove(event) {
    const remove = event.target.closest(".cv-remove");
    if (!remove) return;
    event.preventDefault();
    event.stopPropagation();
    const row = remove.closest("[data-delete]");
    if (row && row.closest(".cv[data-job-id]")) deleteItem(row);
  }

  document.addEventListener("pointerdown", onRemove, true);
  document.addEventListener("click", onRemove, true);

  function syncContactFields(data, current) {
    if (data.full_name) {
      document.querySelectorAll("[data-path='contact.full_name'], [data-path='name']").forEach((el) => {
        if (el !== current) el.textContent = data.full_name;
      });
      document.title = data.full_name;
    }
    if (data.email !== undefined) {
      document.querySelectorAll("[data-path='contact.email']").forEach((el) => {
        if (el !== current) el.textContent = data.email;
      });
    }
    const jobRoot = current && current.closest("[data-job-id]");
    const jobId = jobRoot ? jobRoot.getAttribute("data-job-id") : null;
    if (jobId) {
      try {
        window.parent.postMessage({ type: "cv-contact-changed", jobId: Number(jobId) }, "*");
      } catch {
        /* ignore */
      }
    }
  }

  function persist(item) {
    if (!item || item.dataset.saving === "1") return;
    const path = item.getAttribute("data-path");
    const html = item.innerHTML;
    const jobId = jobIdFor(item);
    if (!path || !jobId) return;
    if (item.dataset.original !== undefined && html === item.dataset.original) return;
    item.dataset.saving = "1";
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
        item.dataset.original = item.innerHTML;
        if (isContactPath(path)) syncContactFields(data, item);
        item.classList.add("is-saved");
        setTimeout(() => item.classList.remove("is-saved"), 700);
      })
      .catch(() => {
        if (item.dataset.original !== undefined) item.innerHTML = item.dataset.original;
        item.classList.add("is-error");
        setTimeout(() => item.classList.remove("is-error"), 1200);
      })
      .finally(() => {
        delete item.dataset.saving;
      });
  }

  function commit(item) {
    if (!item) return;
    item.removeAttribute("contenteditable");
    item.classList.remove("is-editing");
    if (active === item) active = null;
    hideToolbar();
    persist(item);
  }

  function beginEdit(item) {
    if (!item || active === item) return;
    if (active) commit(active);
    active = item;
    if (item.dataset.saving !== "1") item.dataset.original = item.innerHTML;
    item.setAttribute("contenteditable", "true");
    item.classList.add("is-editing");
    item.focus();
    if (!isContactPath(item.getAttribute("data-path"))) {
      placeToolbar(item);
      syncButtons();
    } else {
      hideToolbar();
    }
  }

  document.addEventListener(
    "pointerdown",
    (event) => {
      if (toolbar.contains(event.target)) return;
      if (event.target.closest(".cv-remove")) return;
      const item = event.target.closest("[data-path]");
      if (active && item !== active) commit(active);
    },
    true
  );

  document.addEventListener("click", (event) => {
    if (event.target.closest(".cv-remove")) return;
    const item = event.target.closest("[data-path]");
    if (!item || !item.closest(".cv[data-job-id], .letter[data-job-id], .shokumu[data-job-id]")) return;
    beginEdit(item);
  });

  document.addEventListener("keyup", () => {
    if (active) {
      placeToolbar(active);
      syncButtons();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (!active) return;
    if (event.key === "Enter") {
      event.preventDefault();
      if (allowsLineBreak(active)) {
        document.execCommand("insertLineBreak", false, null);
        return;
      }
      commit(active);
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

  document.addEventListener("paste", (event) => {
    if (!active) return;
    event.preventDefault();
    const text = (event.clipboardData || window.clipboardData).getData("text/plain");
    document.execCommand("insertText", false, text);
  });

  document.addEventListener("focusin", (event) => {
    if (toolbar.contains(event.target)) return;
    if (active && event.target !== active && !active.contains(event.target)) {
      commit(active);
    }
  });

  document.addEventListener(
    "blur",
    (event) => {
      const item = event.target.closest("[data-path]");
      if (!item) return;
      if (suppressBlur) {
        suppressBlur = false;
        return;
      }
      if (item.getAttribute("contenteditable") === "true") commit(item);
    },
    true
  );
})();
