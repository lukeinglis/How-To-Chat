// Per-site selectors. This is the part that breaks when a chat site
// changes its markup; candidates are tried in order, first match wins.
window.HowToChat = window.HowToChat || {};

HowToChat.siteConfigs = {
  "chatgpt.com": {
    editorSelectors: [
      "#prompt-textarea",
      "form [contenteditable='true']",
      "textarea#prompt-textarea",
    ],
    // Used only to tell "fresh chat" from "there's at least one prior
    // exchange" (cue 5's only use of prior turns, see detector.js hasCue5).
    // Content isn't read, so a coarse selector is fine; candidates tried in
    // order, first match wins.
    turnSelectors: [
      "[data-message-author-role]",
      "article[data-testid^='conversation-turn-']",
    ],
  },
};

HowToChat.getSiteConfig = function (hostname) {
  return HowToChat.siteConfigs[hostname] || null;
};
