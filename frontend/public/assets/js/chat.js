/* eslint-disable no-undef */
'use strict';

// ─── State ────────────────────────────────────────────────────
const state = {
  language: APP_CONFIG.language,
  credits: APP_CONFIG.credits,
  hasMessages: false,
  isStreaming: false,
};

// ─── DOM refs ─────────────────────────────────────────────────
const welcomeScreen = document.getElementById('welcome-screen');
const messagesContainer = document.getElementById('messages-container');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const creditsCount = document.getElementById('credits-count');
const creditsHint = document.getElementById('credits-hint');
const langSelect = document.getElementById('language-select');
const userMenuBtn = document.getElementById('user-menu-btn');
const newChatBtn = document.getElementById('new-chat-btn');

// ─── Helpers ──────────────────────────────────────────────────
function updateCredits(newVal) {
  state.credits = newVal;
  creditsCount.textContent = newVal;
  if (creditsHint) creditsHint.textContent = newVal;
}

function showChat() {
  if (!state.hasMessages) {
    state.hasMessages = true;
    welcomeScreen.style.display = 'none';
    messagesContainer.style.display = 'flex';
  }
}

function scrollToBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function createMessageRow(role, content, sourceFile) {
  const row = document.createElement('div');
  row.className = `message-row message-row--${role}`;

  const avatarDiv = document.createElement('div');
  if (role === 'user') {
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = APP_CONFIG.fullName.charAt(0).toUpperCase();
  } else {
    avatarDiv.className = 'message-avatar message-avatar--bot';
    avatarDiv.innerHTML = '<i class="bi bi-robot"></i>';
  }

  const bubble = document.createElement('div');
  bubble.className = `message-bubble message-bubble--${role}`;
  bubble.innerHTML = role === 'user'
    ? escapeHtml(content)
    : renderMarkdown(content); // render markdown for bot

  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'column';
  wrapper.style.alignItems = role === 'user' ? 'flex-end' : 'flex-start';
  wrapper.appendChild(bubble);

  if (sourceFile && role === 'assistant') {
    const src = document.createElement('div');
    src.className = 'message-source';
    src.innerHTML = `<i class="bi bi-file-earmark-text"></i> Source: ${escapeHtml(sourceFile)}`;
    wrapper.appendChild(src);
  }

  row.appendChild(avatarDiv);
  row.appendChild(wrapper);
  return row;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

// Capture the marked.js library reference BEFORE defining our wrapper
// (our function name must not shadow window.marked)
const _markedLib = (typeof window.marked !== 'undefined') ? window.marked : null;

function renderMarkdown(text) {
  if (_markedLib) {
    if (typeof _markedLib.parse === 'function') {
      return _markedLib.parse(text);       // marked v4+
    }
    if (typeof _markedLib === 'function') {
      return _markedLib(text);             // marked v1-v3
    }
  }
  // Plain text fallback
  return escapeHtml(text).replace(/\n/g, '<br>');
}

let _typingInterval = null;

function addTypingIndicator() {
  const row = document.createElement('div');
  row.className = 'message-row';
  row.id = 'typing-indicator';

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar message-avatar--bot';
  avatar.innerHTML = '<i class="bi bi-robot"></i>';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble message-bubble--bot typing-status-bubble';

  const statusMessages = [
    '🤔 Thinking...',
    '🔍 Searching knowledge base...',
    '⚙️ Working...',
    '✍️ Generating response...',
    '⏳ Almost there...',
  ];
  let idx = 0;
  bubble.innerHTML = `<span class="typing-status-text">${statusMessages[0]}</span>`;

  _typingInterval = setInterval(() => {
    idx = (idx + 1) % statusMessages.length;
    const el = bubble.querySelector('.typing-status-text');
    if (el) {
      el.style.opacity = '0';
      setTimeout(() => {
        el.textContent = statusMessages[idx];
        el.style.opacity = '1';
      }, 200);
    }
  }, 2500);

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesContainer.appendChild(row);
  scrollToBottom();
  return row;
}

function removeTypingIndicator() {
  if (_typingInterval) { clearInterval(_typingInterval); _typingInterval = null; }
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

// ─── Send Message ─────────────────────────────────────────────
async function sendMessage(text) {
  if (!text.trim() || state.isStreaming) return;
  if (state.credits <= 0) {
    alert('You have no credits remaining!');
    return;
  }

  showChat();
  state.isStreaming = true;
  sendBtn.disabled = true;

  // User bubble
  const userRow = createMessageRow('user', text);
  messagesContainer.appendChild(userRow);
  scrollToBottom();

  const typingRow = addTypingIndicator();

  try {
    const response = await fetch(`${APP_CONFIG.apiBase}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        language: state.language,
        user_id: APP_CONFIG.userId,
      }),
    });

    removeTypingIndicator();

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    // SSE streaming
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    const botRow = createMessageRow('assistant', '');
    const botBubble = botRow.querySelector('.message-bubble--assistant');
    messagesContainer.appendChild(botRow);

    let fullText = '';
    let sourceFile = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]') break;
          try {
            const parsed = JSON.parse(data);
            if (parsed.token) {
              fullText += parsed.token;
              botBubble.innerHTML = renderMarkdown(fullText);
              scrollToBottom();
            }
            if (parsed.source) sourceFile = parsed.source;
            if (parsed.credits !== undefined) updateCredits(parsed.credits);
            // Admin-only: show LLM prompt inspector popup
            if (parsed.debug_prompt && typeof showPromptPopup === 'function') {
              showPromptPopup(parsed.debug_prompt);
            }
          } catch (_) {
            fullText += data;
            botBubble.innerHTML = renderMarkdown(fullText);
          }
        }
      }
    }

    // Add source citation if present
    if (sourceFile && botBubble) {
      const wrapper = botBubble.parentElement;
      const src = document.createElement('div');
      src.className = 'message-source';
      src.innerHTML = `<i class="bi bi-file-earmark-text"></i> Source: ${escapeHtml(sourceFile)}`;
      wrapper.appendChild(src);
    }

    // Deduct credit locally (server already did it)
    if (state.credits > 0) updateCredits(state.credits - 1);

  } catch (err) {
    removeTypingIndicator();
    const errRow = createMessageRow('assistant', `⚠️ Error: ${err.message}`);
    messagesContainer.appendChild(errRow);
    scrollToBottom();
  } finally {
    state.isStreaming = false;
    chatInput.disabled = false;
    chatInput.focus();
    updateSendBtn();
  }
}

// ─── Input handling ───────────────────────────────────────────
function updateSendBtn() {
  sendBtn.disabled = chatInput.value.trim() === '' || state.isStreaming;
}

chatInput.addEventListener('input', () => {
  // Auto-resize
  chatInput.style.height = 'auto';
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, 140)}px`;
  updateSendBtn();
});

chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (text) {
      chatInput.value = '';
      chatInput.style.height = 'auto';
      updateSendBtn();
      sendMessage(text);
    }
  }
});

sendBtn.addEventListener('click', () => {
  const text = chatInput.value.trim();
  if (text) {
    chatInput.value = '';
    chatInput.style.height = 'auto';
    updateSendBtn();
    sendMessage(text);
  }
});

// ─── Starter Chips ────────────────────────────────────────────
document.querySelectorAll('.chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    const msg = chip.dataset.msg;
    if (msg) sendMessage(msg);
  });
});

// ─── New Chat ─────────────────────────────────────────────────
newChatBtn.addEventListener('click', () => {
  state.hasMessages = false;
  messagesContainer.innerHTML = '';
  messagesContainer.style.display = 'none';
  welcomeScreen.style.display = '';
});

// ─── Language Selector ────────────────────────────────────────
langSelect.addEventListener('change', () => {
  state.language = langSelect.value;
});

// ─── User Menu Toggle ─────────────────────────────────────────
userMenuBtn.addEventListener('click', () => {
  userMenuBtn.classList.toggle('open');
});

document.addEventListener('click', (e) => {
  if (!userMenuBtn.contains(e.target)) {
    userMenuBtn.classList.remove('open');
  }
});

// ─── Capability mode ──────────────────────────────────────────
document.querySelectorAll('.capability-item').forEach((item) => {
  item.addEventListener('click', () => {
    const mode = item.dataset.mode;

    // Quiz → dedicated page
    if (mode === 'quiz') {
      window.location.href = '/quiz.php';
      return;
    }

    // My Scores → dedicated page
    if (mode === 'scores') {
      window.location.href = '/scores.php';
      return;
    }

    document.querySelectorAll('.capability-item').forEach((i) => i.classList.remove('active'));
    item.classList.add('active');

    const modeMessages = {
      rag: 'Ask me about IPL teams, players, records...',
    };
    if (modeMessages[mode]) {
      chatInput.placeholder = modeMessages[mode];
    }
  });
});
