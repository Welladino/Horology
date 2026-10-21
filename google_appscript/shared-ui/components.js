// Safe text-only element builder shared by the two Apps Script interfaces.
window.HorologyUi = Object.freeze({
  element(tag, className, value) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (value !== undefined) el.textContent = value;
    return el;
  }
});
