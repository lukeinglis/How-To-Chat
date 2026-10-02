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
        overlay.update(evaluate(text));
      },
      400
    );
  }

  // Cue 5 (detector.js hasCue5) only checks whether there's a prior turn at
  // all, never its content, so a DOM node count is enough -- no need to read
  // or store message text. Visibility filter matters: ChatGPT leaves the
  // previous conversation's message nodes in the DOM (hidden) when you
  // start a new chat, so an unfiltered count is nonzero even in a fresh one.
  function getPriorTurns() {
    for (const selector of siteConfig.turnSelectors || []) {
      const nodes = Array.from(document.querySelectorAll(selector)).filter(
        (el) => el.offsetParent !== null
      );
      if (nodes.length) return nodes;
    }
    return [];
  }

  // Safety flags take priority: they're higher-stakes (docs/safety.md) and
  // their tips lead the popover, with framing-cue tips following.
  function evaluate(text) {
    const safetyResult = HowToChat.safetyDetector.predict(text);
    const safetyTips = HowToChat.safetyDetector.tipsFor(safetyResult);

    const cueResult = HowToChat.detector.predict(text, getPriorTurns());
    const cueTips = cueResult.cues.map((cue) => HowToChat.detector.tips[cue]).filter(Boolean);

    const tips = safetyTips.concat(cueTips);
    const show = (safetyResult.shouldFlag && safetyTips.length > 0) || (cueResult.shouldFlag && cueTips.length > 0);
    return { show, tips, severity: safetyResult.shouldFlag ? "safety" : "cue" };
  }

  function tick() {
    const editorEl = findEditor();
    if (editorEl && editorEl.isConnected) {
      attach(editorEl);
    } else if (currentEditor && !currentEditor.isConnected) {
      currentEditor = null;
      overlay.update({ show: false, tips: [], severity: "cue" });
    }
  }

  const observer = new MutationObserver(tick);
  observer.observe(document.body, { childList: true, subtree: true });
  tick();
})();
