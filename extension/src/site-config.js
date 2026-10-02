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
    // Content isn't read, so a coarse selector is fine. Verified against
    // live chatgpt.com markup -- data-message-author-role and
    // article[data-testid^='conversation-turn-'] don't exist there.
    // ChatGPT also leaves the previous conversation's bubbles in the DOM
    // (hidden) when you start a new chat, so a raw node count isn't enough;
    // content.js filters to visible nodes only.
    turnSelectors: ["[data-user-message-bubble]"],
  },
};

HowToChat.getSiteConfig = function (hostname) {
  return HowToChat.siteConfigs[hostname] || null;
};
