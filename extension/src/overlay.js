// Badge + popover in a shadow root, appended to document.body directly
// so the only footprint on the site's DOM is the one host element.
// Positioned via the anchor element's bounding rect, never inserted
// into the site's own tree.
window.HowToChat = window.HowToChat || {};

(function () {
  const STYLE = `
    :host { all: initial; }
    .badge {
      position: fixed;
      z-index: 2147483647;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 22px;
      height: 22px;
      border-radius: 999px;
      background: #b45309;
      color: #fff;
      font: 600 12px/1 system-ui, sans-serif;
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    }
    .badge:hover { background: #92400e; }
    .badge.safety { background: #b91c1c; }
    .badge.safety:hover { background: #991b1b; }
    .popover {
      position: fixed;
      z-index: 2147483647;
      max-width: 280px;
      background: #1f2937;
      color: #f9fafb;
      font: 400 13px/1.4 system-ui, sans-serif;
      padding: 10px 12px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
    }
    .popover ul { margin: 0; padding-left: 18px; }
    .popover li + li { margin-top: 6px; }
    .hidden { display: none; }
  `;

  class Overlay {
    constructor() {
      this.host = document.createElement("div");
      this.host.setAttribute("data-how-to-chat", "");
      const shadow = this.host.attachShadow({ mode: "closed" });

      const style = document.createElement("style");
      style.textContent = STYLE;
      shadow.appendChild(style);

      this.badge = document.createElement("div");
      this.badge.className = "badge hidden";
      this.badge.textContent = "!";
      this.badge.addEventListener("click", () => this.togglePopover());
      shadow.appendChild(this.badge);

      this.popover = document.createElement("div");
      this.popover.className = "popover hidden";
      shadow.appendChild(this.popover);

      this.anchor = null;
      this.tips = [];
      this.popoverOpen = false;

      document.body.appendChild(this.host);
      this._onReposition = () => this.reposition();
      window.addEventListener("scroll", this._onReposition, true);
      window.addEventListener("resize", this._onReposition);
    }

    mount(anchorEl) {
      this.anchor = anchorEl;
      this.reposition();
    }

    update(result) {
      this.tips = result.tips;
      this.badge.classList.toggle("hidden", !result.show);
      this.badge.classList.toggle("safety", result.severity === "safety");
      if (!result.show) this.closePopover();
      this.reposition();
    }

    togglePopover() {
      if (this.popoverOpen) this.closePopover();
      else this.openPopover();
    }

    openPopover() {
      this.popover.innerHTML =
        "<ul>" + this.tips.map((t) => `<li>${escapeHtml(t)}</li>`).join("") + "</ul>";
      this.popover.classList.remove("hidden");
      this.popoverOpen = true;
      this.reposition();
    }

    closePopover() {
      this.popover.classList.add("hidden");
      this.popoverOpen = false;
    }

    reposition() {
      if (!this.anchor || !this.anchor.isConnected) return;
      const rect = this.anchor.getBoundingClientRect();
      const badgeTop = rect.top + 8;
      const badgeLeft = rect.right - 30;
      this.badge.style.top = `${badgeTop}px`;
      this.badge.style.left = `${badgeLeft}px`;
      if (this.popoverOpen) {
        this.popover.style.top = `${badgeTop + 26}px`;
        this.popover.style.left = `${Math.max(8, badgeLeft - 258)}px`;
      }
    }

    destroy() {
      window.removeEventListener("scroll", this._onReposition, true);
      window.removeEventListener("resize", this._onReposition);
      this.host.remove();
    }
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  HowToChat.Overlay = Overlay;
})();
