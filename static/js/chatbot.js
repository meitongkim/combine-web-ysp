/**
 * YSP Verdi AI Chatbot Widget
 * Dynamically builds the floating chatbot UI and communicates with the /api/chat Flask backend.
 */

(function () {
  "use strict";

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
