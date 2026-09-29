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
  },
};

HowToChat.getSiteConfig = function (hostname) {
  return HowToChat.siteConfigs[hostname] || null;
};
