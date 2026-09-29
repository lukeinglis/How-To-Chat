// Reads the editor's text on input, debounced. Never writes to it.
// Some rich-text editors (e.g. ChatGPT's ProseMirror composer) don't fire a
// native "input" event for every edit -- select-all + delete clears the DOM
// without one, so a plain "input" listener misses it. A MutationObserver on
// the editor catches those cases too.
window.HowToChat = window.HowToChat || {};

(function () {
  function watchInput(editorEl, onChange, debounceMs) {
    let timer = null;
    const fire = () => {
      clearTimeout(timer);
      timer = setTimeout(() => onChange(editorEl.innerText || editorEl.value || ""), debounceMs);
    };
    editorEl.addEventListener("input", fire);
    const observer = new MutationObserver(fire);
    observer.observe(editorEl, { childList: true, subtree: true, characterData: true });
    fire();
    return () => {
      clearTimeout(timer);
      editorEl.removeEventListener("input", fire);
      observer.disconnect();
    };
  }

  HowToChat.watchInput = watchInput;
})();
