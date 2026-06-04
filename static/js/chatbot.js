/**
 * YSP Verdi AI Chatbot Widget
 * Dynamically builds the floating chatbot UI and communicates with the /api/chat Flask backend.
 */

(function () {
  "use strict";

  // ─── Dynamic Language Selector Injection ───────────────────────────────
  (function injectLanguageSelectorCSSAndMarkup() {
    if (document.getElementById("langSelector")) return;

    // 1. Language selector CSS rules
    const langStyles = `
      .lang-selector {
        position: relative;
        display: inline-flex;
        align-items: center;
        padding-left: 12px;
        border-left: 1px solid rgba(31, 42, 34, 0.10);
        margin-left: auto;
      }
      .lang-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.6);
        font-size: 13px;
        font-weight: 500;
        color: #3d4b40;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
        white-space: nowrap;
        font-family: inherit;
      }
      .lang-btn:hover {
        background: rgba(255, 255, 255, 0.85);
        border-color: #9ab078;
        color: #1f2a22;
        transform: translateY(-1px);
      }
      .globe-svg {
        width: 14px;
        height: 14px;
        stroke: #89a36c;
        transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
        fill: none;
      }
      .lang-btn:hover .globe-svg {
        transform: rotate(20deg) scale(1.1);
      }
      .lang-arrow {
        width: 8px;
        height: 8px;
        stroke: #67756a;
        transition: transform 0.25s ease;
        fill: none;
      }
      .lang-selector.open .lang-arrow {
        transform: rotate(180deg);
      }
      .lang-dropdown {
        position: absolute;
        top: calc(100% + 12px);
        right: 0;
        background: rgba(255, 255, 255, 0.60);
        backdrop-filter: blur(16px) saturate(1.4);
        -webkit-backdrop-filter: blur(16px) saturate(1.4);
        border: 1px solid rgba(255, 255, 255, 0.75);
        border-radius: 18px;
        box-shadow: 0 1px 2px rgba(31, 42, 34, 0.06), 0 24px 60px -20px rgba(122, 150, 108, 0.30);
        padding: 6px;
        min-width: 155px;
        opacity: 0;
        transform: translateY(10px) scale(0.95);
        pointer-events: none;
        visibility: hidden;
        transition: opacity 0.25s cubic-bezier(0.2, 0.8, 0.2, 1),
                    transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1),
                    visibility 0.25s;
        display: flex;
        flex-direction: column;
        list-style: none;
        margin: 0;
        z-index: 10000;
        padding-left: 0;
      }
      .lang-selector.open .lang-dropdown {
        opacity: 1;
        transform: translateY(0) scale(1);
        pointer-events: auto;
        visibility: visible;
      }
      .lang-option {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 14px;
        border-radius: 12px;
        font-size: 13.5px;
        color: #3d4b40;
        transition: background 0.2s, color 0.2s, transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
        cursor: pointer;
        white-space: nowrap;
        text-align: left;
      }
      .lang-option:hover {
        background: rgba(154, 176, 120, 0.14);
        color: #89a36c;
        transform: translateX(4px);
      }
      .lang-option.active {
        font-weight: 600;
        color: #89a36c;
        background: rgba(154, 176, 120, 0.08);
      }
      .lang-selector + .nav-user {
        border-left: none;
        padding-left: 0;
        margin-left: 12px;
      }
      .lang-selector + .btn-primary {
        margin-left: 12px;
      }

      /* Google Translate Overrides */
      .goog-te-banner-frame,
      .goog-te-banner,
      .goog-te-menu-value,
      .goog-te-menu2-frame,
      .goog-te-balloon-frame {
        display: none !important;
      }
      body {
        top: 0 !important;
        position: static !important;
      }
      .skiptranslate {
        display: none !important;
      }
      font[style*="background-color"] {
        background-color: transparent !important;
        box-shadow: none !important;
      }

      @media (max-width: 980px) {
        .lang-selector {
          border-left: none;
          padding-left: 0;
          margin-left: auto;
        }
      }
      @media (max-width: 640px) {
        .lang-selector {
          padding-left: 0;
          margin-left: auto;
        }
        .lang-text {
          display: none;
        }
        .lang-btn {
          padding: 6px 8px;
        }
        .lang-dropdown {
          right: -40px;
        }
      }
    `;

    // Inject styles
    const styleEl = document.createElement("style");
    styleEl.className = "lang-selector-styles";
    styleEl.textContent = langStyles;
    document.head.appendChild(styleEl);

    // Dynamic builder logic
    function tryInjectSelector() {
      if (document.getElementById("langSelector")) return;

      const navElement = document.querySelector("#navWrap nav") || document.querySelector("nav.nav");
      if (!navElement) return;

      const langSelector = document.createElement("div");
      langSelector.className = "lang-selector notranslate";
      langSelector.id = "langSelector";

      langSelector.innerHTML = `
        <button class="lang-btn" id="langBtn" aria-expanded="false" aria-haspopup="listbox">
          <svg class="globe-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
          <span class="lang-text" id="currentLangText">English</span>
          <svg class="lang-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </button>
        <ul class="lang-dropdown" id="langDropdown" role="listbox" aria-label="Language selection">
          <li role="option" data-lang="en" class="lang-option active">🇺🇸 English</li>
          <li role="option" data-lang="es" class="lang-option">🇪🇸 Español</li>
          <li role="option" data-lang="zh-CN" class="lang-option">🇨🇳 中文</li>
          <li role="option" data-lang="fr" class="lang-option">🇫🇷 Français</li>
          <li role="option" data-lang="ms" class="lang-option">🇲🇾 Melayu</li>
          <li role="option" data-lang="ta" class="lang-option">🇮🇳 தமிழ்</li>
          <li role="option" data-lang="hi" class="lang-option">🇮🇳 हिन्दी</li>
        </ul>
      `;

      // Insert before Join button or right side profile block
      const actionBtn = navElement.querySelector(".btn-primary") || navElement.querySelector(".btn") || navElement.querySelector(".nav-user");
      if (actionBtn) {
        navElement.insertBefore(langSelector, actionBtn);
      } else {
        navElement.appendChild(langSelector);
      }

      const langBtn = document.getElementById("langBtn");
      const currentLangText = document.getElementById("currentLangText");
      const langOptions = langSelector.querySelectorAll(".lang-option");

      // Cookie Helpers
      function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
      }

      function setCookie(name, value, days) {
        let expires = "";
        if (days) {
          const date = new Date();
          date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
          expires = "; expires=" + date.toUTCString();
        }
        document.cookie = `${name}=${value || ""}${expires}; path=/;`;
        document.cookie = `${name}=${value || ""}${expires}; path=/; domain=${window.location.hostname};`;
      }

      function deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`;
      }

      // Check current language cookie
      const transCookie = getCookie("googtrans");
      let currentLang = "en";

      if (transCookie) {
        const parts = transCookie.split("/");
        if (parts.length >= 3) {
          currentLang = parts[2];
        }
      }

      let selectedOptionFound = false;
      langOptions.forEach((option) => {
        const optLang = option.getAttribute("data-lang");
        if (optLang === currentLang) {
          option.classList.add("active");
          if (currentLangText) {
            const textContent = option.textContent.trim();
            const words = textContent.split(" ");
            currentLangText.textContent = words.slice(1).join(" ");
          }
          selectedOptionFound = true;
        } else {
          option.classList.remove("active");
        }
      });

      if (!selectedOptionFound && currentLang === "en" && currentLangText) {
        currentLangText.textContent = "English";
      }

      // Dropdown toggle trigger
      langBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const isOpen = langSelector.classList.toggle("open");
        langBtn.setAttribute("aria-expanded", isOpen);
      });

      // Close on outside click
      document.addEventListener("click", (e) => {
        if (!langSelector.contains(e.target)) {
          langSelector.classList.remove("open");
          langBtn.setAttribute("aria-expanded", "false");
        }
      });

      // Handle language swap clicks
      langOptions.forEach((option) => {
        option.addEventListener("click", (e) => {
          e.stopPropagation();
          const selectedLang = option.getAttribute("data-lang");

          if (selectedLang === "en") {
            deleteCookie("googtrans");
          } else {
            setCookie("googtrans", `/en/${selectedLang}`, 30);
          }

          langSelector.classList.remove("open");
          langBtn.setAttribute("aria-expanded", "false");
          window.location.reload();
        });
      });

      // Load Google Translate script dynamically if not present
      if (!document.querySelector('script[src*="translate.google.com"]')) {
        if (!document.getElementById("google_translate_element")) {
          const translateDiv = document.createElement("div");
          translateDiv.id = "google_translate_element";
          translateDiv.style.display = "none";
          document.body.appendChild(translateDiv);
        }

        window.googleTranslateElementInit = function() {
          new google.translate.TranslateElement({
            pageLanguage: 'en',
            layout: google.translate.TranslateElement.InlineLayout.SIMPLE,
            autoDisplay: false
          }, 'google_translate_element');
        };

        const script = document.createElement("script");
        script.type = "text/javascript";
        script.src = "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
        document.head.appendChild(script);
      }
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", tryInjectSelector);
    } else {
      tryInjectSelector();
    }
  })();

  // Prevent multiple initializations
  if (document.getElementById("yspChatWidget")) return;

  // 1. Inject Stylesheets
  const styles = `
    /* Floating Widget container */
    #yspChatWidget {
      position: fixed;
      right: 24px;
      bottom: 24px;
      z-index: 9999;
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* Toggle Button */
    #yspChatToggle {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #e8f0d8, #d4e4b8);
      border: 2px solid rgba(137, 163, 108, 0.4);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 8px 32px rgba(31, 42, 34, 0.25);
      transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      font-size: 24px;
      position: relative;
      padding: 0;
      overflow: hidden;
    }
    #yspChatToggle img {
      width: 100%;
      height: 100%;
      border-radius: 50%;
      object-fit: cover;
    }
    #yspChatToggle:hover {
      transform: scale(1.08) translateY(-2px);
      box-shadow: 0 12px 40px rgba(31, 42, 34, 0.35);
      border-color: rgba(137, 163, 108, 0.7);
    }
    #yspChatToggle:active {
      transform: scale(0.95);
    }
    #yspChatToggle .pulse-ring {
      position: absolute;
      border: 1px solid #89a36c;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      animation: yspPulse 2.4s infinite;
      opacity: 0;
      pointer-events: none;
    }
    @keyframes yspPulse {
      0% { transform: scale(1); opacity: 0.6; }
      100% { transform: scale(1.6); opacity: 0; }
    }

    /* Chat Window */
    #yspChatWindow {
      position: absolute;
      bottom: 72px;
      right: 0;
      width: 360px;
      height: 500px;
      max-height: calc(100vh - 120px);
      background: rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(20px) saturate(1.8);
      -webkit-backdrop-filter: blur(20px) saturate(1.8);
      border: 1px solid rgba(31, 42, 34, 0.12);
      border-radius: 20px;
      box-shadow: 0 16px 64px -8px rgba(31, 42, 34, 0.22);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      opacity: 0;
      transform: translateY(24px) scale(0.95);
      pointer-events: none;
      transition: all 0.35s cubic-bezier(0.165, 0.84, 0.44, 1);
      transform-origin: bottom right;
    }
    #yspChatWindow.open {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: auto;
    }

    /* Header */
    .ysp-chat-header {
      padding: 16px 20px;
      background: rgba(31, 42, 34, 0.95);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .ysp-chat-header .title-area {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .ysp-chat-header .avatar {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: #d4e4b8;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      border: 1px solid rgba(255, 255, 255, 0.25);
      overflow: hidden;
      padding: 0;
    }
    .ysp-chat-header .avatar img {
      width: 100%;
      height: 100%;
      border-radius: 50%;
      object-fit: cover;
    }
    .ysp-chat-header .info {
      display: flex;
      flex-direction: column;
    }
    .ysp-chat-header h4 {
      margin: 0;
      font-size: 14.5px;
      font-weight: 600;
      letter-spacing: -0.01em;
      font-family: 'Fraunces', serif;
    }
    .ysp-chat-header .status {
      font-size: 11px;
      opacity: 0.8;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .ysp-chat-header .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: #4ade80;
      display: inline-block;
      box-shadow: 0 0 8px #4ade80;
      animation: yspLiveDot 1.6s infinite alternate;
    }
    @keyframes yspLiveDot {
      0% { opacity: 0.4; }
      100% { opacity: 1; }
    }
    .ysp-chat-close {
      background: none;
      border: none;
      color: rgba(255, 255, 255, 0.7);
      cursor: pointer;
      font-size: 16px;
      padding: 4px;
      transition: color 0.2s;
    }
    .ysp-chat-close:hover {
      color: #ffffff;
    }

    /* Message Area */
    .ysp-chat-messages {
      flex: 1;
      padding: 16px 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      scroll-behavior: smooth;
    }

    /* Message Bubbles */
    .ysp-msg {
      max-width: 82%;
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 13.5px;
      line-height: 1.45;
      word-wrap: break-word;
      animation: yspFadeInUp 0.3s ease forwards;
    }
    @keyframes yspFadeInUp {
      0% { opacity: 0; transform: translateY(8px); }
      100% { opacity: 1; transform: translateY(0); }
    }
    .ysp-msg.bot {
      align-self: flex-start;
      background: #f1f5f2;
      color: #1f2a22;
      border-bottom-left-radius: 4px;
      border: 1px solid rgba(31, 42, 34, 0.06);
    }
    .ysp-msg.user {
      align-self: flex-end;
      background: #1f2a22;
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }
    .ysp-msg p {
      margin: 0 0 8px 0;
    }
    .ysp-msg p:last-child {
      margin-bottom: 0;
    }
    .ysp-msg b, .ysp-msg strong {
      font-weight: 600;
      color: inherit;
    }

    /* Suggestion Chips */
    .ysp-chat-suggestions {
      padding: 8px 16px 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      border-top: 1px solid rgba(31, 42, 34, 0.05);
      background: rgba(255, 255, 255, 0.4);
    }
    .ysp-chip {
      background: #ffffff;
      border: 1px solid rgba(31, 42, 34, 0.12);
      border-radius: 12px;
      padding: 6px 12px;
      font-size: 11.5px;
      color: #3d4b40;
      cursor: pointer;
      transition: all 0.2s;
      font-weight: 500;
    }
    .ysp-chip:hover {
      background: #f3f7f4;
      border-color: #89a36c;
      color: #1f2a22;
      transform: translateY(-1px);
    }

    /* Input Footer */
    .ysp-chat-footer {
      padding: 12px 16px;
      background: #ffffff;
      border-top: 1px solid rgba(31, 42, 34, 0.08);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .ysp-chat-footer input {
      flex: 1;
      border: 1px solid rgba(31, 42, 34, 0.15);
      border-radius: 12px;
      padding: 10px 14px;
      font-size: 13.5px;
      font-family: inherit;
      outline: none;
      background: #fbfdfa;
      transition: all 0.2s;
    }
    .ysp-chat-footer input:focus {
      border-color: #89a36c;
      box-shadow: 0 0 0 3px rgba(137, 163, 108, 0.15);
      background: #ffffff;
    }
    .ysp-chat-send {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: #1f2a22;
      border: none;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background 0.2s, transform 0.2s;
    }
    .ysp-chat-send:hover {
      background: #2d3f32;
      transform: scale(1.03);
    }
    .ysp-chat-send:active {
      transform: scale(0.95);
    }
    .ysp-chat-send svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }

    /* Typing indicator */
    .ysp-typing {
      display: flex;
      gap: 4px;
      padding: 4px 6px;
      align-items: center;
      justify-content: center;
      height: 14px;
    }
    .ysp-typing span {
      width: 6px;
      height: 6px;
      background: #89a36c;
      border-radius: 50%;
      animation: yspBounce 1.2s infinite ease-in-out;
      opacity: 0.7;
    }
    .ysp-typing span:nth-child(2) { animation-delay: 0.2s; }
    .ysp-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes yspBounce {
      0%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-5px); }
    }

    /* Scrollbars */
    .ysp-chat-messages::-webkit-scrollbar {
      width: 5px;
    }
    .ysp-chat-messages::-webkit-scrollbar-track {
      background: transparent;
    }
    .ysp-chat-messages::-webkit-scrollbar-thumb {
      background: rgba(31, 42, 34, 0.15);
      border-radius: 99px;
    }

    /* Mobile adjustments */
    @media (max-width: 480px) {
      #yspChatWidget {
        right: 16px;
        bottom: 16px;
      }
      #yspChatWindow {
        width: calc(100vw - 32px);
        height: 460px;
        bottom: 64px;
      }
    }
  `;

  // Inject Styles into Head
  const styleEl = document.createElement("style");
  styleEl.textContent = styles;
  document.head.appendChild(styleEl);

  // 2. Build and Inject DOM Nodes
  const widgetContainer = document.createElement("div");
  widgetContainer.id = "yspChatWidget";

  widgetContainer.innerHTML = `
    <button id="yspChatToggle" aria-label="Open Chat">
      <span class="pulse-ring"></span>
      <img src="/static/img/verdi_mascot.png" alt="Verdi" />
    </button>
    <div id="yspChatWindow">
      <div class="ysp-chat-header">
        <div class="title-area">
          <div class="avatar"><img src="/static/img/verdi_mascot.png" alt="Verdi" /></div>
          <div class="info">
            <h4>Verdi</h4>
            <div class="status"><span class="status-dot"></span> YSP Mascot</div>
          </div>
        </div>
        <button class="ysp-chat-close" aria-label="Close Chat">✕</button>
      </div>
      <div class="ysp-chat-messages" id="yspChatMessages"></div>
      <div class="ysp-chat-suggestions" id="yspChatSuggestions"></div>
      <div class="ysp-chat-footer">
        <input type="text" id="yspChatInput" placeholder="Ask Verdi a question..." autocomplete="off" />
        <button class="ysp-chat-send" id="yspChatSend" aria-label="Send Message">
          <svg viewBox="0 0 24 24">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(widgetContainer);

  // DOM Elements
  const chatToggle = document.getElementById("yspChatToggle");
  const chatWindow = document.getElementById("yspChatWindow");
  const chatClose = document.querySelector(".ysp-chat-close");
  const chatMessages = document.getElementById("yspChatMessages");
  const chatSuggestions = document.getElementById("yspChatSuggestions");
  const chatInput = document.getElementById("yspChatInput");
  const chatSend = document.getElementById("yspChatSend");

  // Chat state
  let chatHistory = []; // format: { role: 'user'|'model', content: string }
  let hasOpened = false;

  // Pre-defined suggestions
  const suggestions = [
    "What is YSP?",
    "Tell me about YSP Learns",
    "How can I join?",
    "Who is Verdi?"
  ];

  // Helper: Format bold and newlines in messages
  function formatMarkdown(text) {
    let html = text;
    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Newlines to <br> or paragraphs
    html = html.split("\n\n").map(para => `<p>${para.replace(/\n/g, "<br>")}</p>`).join("");
    return html;
  }

  // Add a message to the window log
  function addMessage(role, content) {
    const isBot = role === "model" || role === "assistant";
    const msgEl = document.createElement("div");
    msgEl.className = `ysp-msg ${isBot ? "bot" : "user"}`;
    msgEl.innerHTML = formatMarkdown(content);
    chatMessages.appendChild(msgEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Track in state (mapping roles to standard format for backend api)
    chatHistory.push({
      role: isBot ? "assistant" : "user",
      content: content
    });
  }

  // Add Verdi typing indicator
  function showTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.className = "ysp-msg bot";
    indicator.id = "yspTypingIndicator";
    indicator.innerHTML = `
      <div class="ysp-typing">
        <span></span>
        <span></span>
        <span></span>
      </div>
    `;
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Remove Verdi typing indicator
  function removeTypingIndicator() {
    const indicator = document.getElementById("yspTypingIndicator");
    if (indicator) indicator.remove();
  }

  // Fetch response from Flask backend
  async function fetchReply(query) {
    // Keep last 10 messages of conversation history to stay in memory
    const historyToSend = chatHistory.slice(-10);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: historyToSend })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data.message || "Oops! I encountered an error. Please try again.";
    } catch (err) {
      console.error("Chatbot fetch error:", err);
      return "Sorry, I'm having trouble connecting to my brain right now. 🌿 (Connection Error)";
    }
  }

  // Handle message sending
  async function handleSendMessage(text) {
    const query = text.trim();
    if (!query) return;

    chatInput.value = "";
    addMessage("user", query);

    showTypingIndicator();

    const reply = await fetchReply(query);

    removeTypingIndicator();
    addMessage("model", reply);
  }

  // Initialize Suggestions chips
  function renderSuggestions() {
    chatSuggestions.innerHTML = "";
    suggestions.forEach(s => {
      const chip = document.createElement("button");
      chip.className = "ysp-chip";
      chip.textContent = s;
      chip.addEventListener("click", () => {
        handleSendMessage(s);
      });
      chatSuggestions.appendChild(chip);
    });
  }

  // Welcome message when chat is opened first time
  function triggerWelcome() {
    if (hasOpened) return;
    hasOpened = true;
    showTypingIndicator();
    setTimeout(() => {
      removeTypingIndicator();
      addMessage("assistant", "Hi there! I'm **Verdi**, the mascot of YSP. 🌿💚\n\nHow can I help you today? Feel free to ask about our organization, programme routes, or YSP Learns modules!");
      renderSuggestions();
    }, 750);
  }

  // Event Listeners
  chatToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    chatWindow.classList.toggle("open");
    if (chatWindow.classList.contains("open")) {
      triggerWelcome();
      chatInput.focus();
    }
  });

  chatClose.addEventListener("click", (e) => {
    e.stopPropagation();
    chatWindow.classList.remove("open");
  });

  // Close when clicking outside chat widget
  document.addEventListener("click", (e) => {
    if (!widgetContainer.contains(e.target) && chatWindow.classList.contains("open")) {
      chatWindow.classList.remove("open");
    }
  });

  // Prevent closing when clicking inside chat window
  chatWindow.addEventListener("click", (e) => {
    e.stopPropagation();
  });

  // Sending message triggers
  chatSend.addEventListener("click", () => {
    handleSendMessage(chatInput.value);
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      handleSendMessage(chatInput.value);
    }
  });

})();
