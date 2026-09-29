// Entry point. Finds the editor (mounted async on an SPA, so this
// watches for it rather than assuming it's present at document_idle),
// wires input -> detector -> overlay, and re-attaches if the editor
// element gets replaced (chat sites swap it out on navigation).
(function () {
  const siteConfig = HowToChat.getSiteConfig(window.location.hostname);
  if (!siteConfig) return;

  const overlay = new HowToChat.Overlay();
  let stopWatching = null;
  let currentEditor = null;

  function findEditor() {
    for (const selector of siteConfig.editorSelectors) {
      const el = document.querySelector(selector);
      if (el) return el;
    }
    return null;
  }

  function attach(editorEl) {
    if (editorEl === currentEditor) return;
    if (stopWatching) stopWatching();
    currentEditor = editorEl;
    overlay.mount(editorEl);
    stopWatching = HowToChat.watchInput(
      editorEl,
      (text) => {
        const result = HowToChat.detector.predict(text, []);
        overlay.update(result, HowToChat.detector.tips);
      },
      400
    );
  }

  function tick() {
    const editorEl = findEditor();
    if (editorEl && editorEl.isConnected) {
      attach(editorEl);
    } else if (currentEditor && !currentEditor.isConnected) {
      currentEditor = null;
      overlay.update({ shouldFlag: false, cues: [] }, HowToChat.detector.tips);
    }
  }

  const observer = new MutationObserver(tick);
  observer.observe(document.body, { childList: true, subtree: true });
  tick();
})();
