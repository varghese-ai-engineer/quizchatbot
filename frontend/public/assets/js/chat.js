/* eslint-disable no-undef */
'use strict';

// ─── State ────────────────────────────────────────────────────
const state = {
  language: APP_CONFIG.language,
  credits: APP_CONFIG.credits,
  hasMessages: false,
  isStreaming: false,
  abortController: null,   // active AbortController for in-flight request
};

// ─── DOM refs ─────────────────────────────────────────────────
const welcomeScreen      = document.getElementById('welcome-screen');
const messagesContainer  = document.getElementById('messages-container');
const chatInput          = document.getElementById('chat-input');
const sendBtn            = document.getElementById('send-btn');
const creditsCount       = document.getElementById('credits-count');
const creditsHint        = document.getElementById('credits-hint');
const langSelect         = document.getElementById('language-select');
const userMenuBtn        = document.getElementById('user-menu-btn');
const newChatBtn         = document.getElementById('new-chat-btn');

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

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

// Capture the marked.js library reference BEFORE defining our wrapper
const _markedLib = (typeof window.marked !== 'undefined') ? window.marked : null;

function renderMarkdown(text) {
  if (_markedLib) {
    if (typeof _markedLib.parse === 'function') return _markedLib.parse(text);
    if (typeof _markedLib === 'function')       return _markedLib(text);
  }
  return escapeHtml(text).replace(/\n/g, '<br>');
}

// ─── Message Rows ─────────────────────────────────────────────
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
  bubble.innerHTML = role === 'user' ? escapeHtml(content) : renderMarkdown(content);

  const wrapper = document.createElement('div');
  wrapper.style.cssText = `display:flex;flex-direction:column;align-items:${role === 'user' ? 'flex-end' : 'flex-start'}`;
  wrapper.appendChild(bubble);

  if (sourceFile && role === 'assistant') {
    wrapper.appendChild(_makeSourceEl(sourceFile));
  }

  row.appendChild(avatarDiv);
  row.appendChild(wrapper);
  return row;
}

function _makeSourceEl(sourceFile) {
  const src = document.createElement('div');
  src.className = 'message-source';
  src.innerHTML = `<i class="bi bi-file-earmark-text"></i> Source: ${escapeHtml(sourceFile)}`;
  return src;
}

// ─── Typing Indicator ─────────────────────────────────────────
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
      setTimeout(() => { el.textContent = statusMessages[idx]; el.style.opacity = '1'; }, 200);
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

// ─── Streaming Cursor ──────────────────────────────────────────
function _addCursor(bubble) {
  const cursor = document.createElement('span');
  cursor.className = 'streaming-cursor';
  cursor.id = 'streaming-cursor';
  bubble.appendChild(cursor);
}

function _removeCursor() {
  const c = document.getElementById('streaming-cursor');
  if (c) c.remove();
}

// ─── Send Button State ────────────────────────────────────────
function _setStopMode(on) {
  if (on) {
    sendBtn.innerHTML = '<i class="bi bi-stop-fill"></i>';
    sendBtn.classList.add('send-btn--stop');
    sendBtn.disabled = false;
    sendBtn.title = 'Stop generating';
  } else {
    sendBtn.innerHTML = '<i class="bi bi-arrow-up-short"></i>';
    sendBtn.classList.remove('send-btn--stop');
    sendBtn.title = '';
    updateSendBtn();
  }
}

// ─── Robust SSE Stream Parser ─────────────────────────────────
/**
 * Async generator that reads a fetch Response body and yields
 * parsed SSE event objects: { event, data }.
 *
 * Handles the case where a single SSE line is split across
 * multiple network chunks (the main bug in the old code).
 */
async function* parseSSEStream(response) {
  const reader  = response.body.getReader();
  const decoder = new TextDecoder();
  let   buffer  = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Append decoded bytes to the line buffer
      buffer += decoder.decode(value, { stream: true });

      // SSE spec: events are separated by blank lines (\n\n)
      const blocks = buffer.split('\n\n');
      // Keep the last (potentially incomplete) block in the buffer
      buffer = blocks.pop();

      for (const block of blocks) {
        if (!block.trim()) continue;

        let eventType = 'message';
        let dataLines = [];

        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trim());
          }
          // 'retry:', 'id:', and comment lines (':', heartbeat) are ignored
        }

        if (dataLines.length > 0) {
          yield { event: eventType, data: dataLines.join('\n') };
        }
      }
    }
  } finally {
    reader.cancel();
  }
}

// ─── Send Message ─────────────────────────────────────────────
async function sendMessage(text) {
  if (!text.trim()) return;
  if (state.credits <= 0) { alert('You have no credits remaining!'); return; }

  // Abort any in-flight request
  if (state.abortController) {
    state.abortController.abort();
    state.abortController = null;
  }

  showChat();
  state.isStreaming = true;
  chatInput.disabled = true;
  _setStopMode(true);
  _removeCursor();

  // User bubble
  messagesContainer.appendChild(createMessageRow('user', text));
  scrollToBottom();

  const typingRow = addTypingIndicator();
  const ctrl = new AbortController();
  state.abortController = ctrl;

  // Bot bubble (created after typing indicator removed)
  let botBubble   = null;
  let fullText    = '';
  let sourceFile  = null;
  let rafPending  = false;

  // Batched render via requestAnimationFrame
  function scheduleRender() {
    if (rafPending) return;
    rafPending = true;
    requestAnimationFrame(() => {
      rafPending = false;
      if (botBubble) {
        // Preserve cursor node, replace HTML before it
        _removeCursor();
        botBubble.innerHTML = renderMarkdown(fullText);
        if (state.isStreaming) _addCursor(botBubble);
        scrollToBottom();
      }
    });
  }

  try {
    const response = await fetch(`${APP_CONFIG.apiBase}/api/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: text, language: state.language, user_id: APP_CONFIG.userId }),
      signal:  ctrl.signal,
    });

    removeTypingIndicator();

    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    // Create bot bubble
    const botRow = createMessageRow('assistant', '');
    botBubble = botRow.querySelector('.message-bubble--assistant');
    messagesContainer.appendChild(botRow);
    _addCursor(botBubble);
    scrollToBottom();

    // Consume SSE stream
    for await (const { event, data } of parseSSEStream(response)) {

      if (event === 'done' || data === '[DONE]') break;

      if (event === 'token') {
        try {
          const parsed = JSON.parse(data);
          if (parsed.token) { fullText += parsed.token; scheduleRender(); }
        } catch (_) {
          fullText += data;
          scheduleRender();
        }
        continue;
      }

      if (event === 'meta') {
        try {
          const parsed = JSON.parse(data);
          if (parsed.source)      sourceFile = parsed.source;
          if (parsed.credits !== undefined) updateCredits(parsed.credits);
          if (parsed.debug_prompt && typeof showPromptPopup === 'function') {
            showPromptPopup(parsed.debug_prompt);
          }
        } catch (_) { /* ignore malformed meta */ }
        continue;
      }

      // Legacy support: old-style bare data frames (no event type)
      if (event === 'message') {
        try {
          const parsed = JSON.parse(data);
          if (parsed.token)   { fullText += parsed.token; scheduleRender(); }
          if (parsed.source)    sourceFile = parsed.source;
          if (parsed.credits !== undefined) updateCredits(parsed.credits);
          if (parsed.debug_prompt && typeof showPromptPopup === 'function') {
            showPromptPopup(parsed.debug_prompt);
          }
        } catch (_) { /* ignore */ }
      }
    }

    // Final render — remove cursor, show source citation
    _removeCursor();
    if (botBubble) {
      botBubble.innerHTML = renderMarkdown(fullText);
      if (sourceFile) botBubble.parentElement.appendChild(_makeSourceEl(sourceFile));
    }

  } catch (err) {
    _removeCursor();
    removeTypingIndicator();

    if (err.name === 'AbortError') {
      // User cancelled — show partial response if any
      if (botBubble && fullText) {
        _removeCursor();
        botBubble.innerHTML = renderMarkdown(fullText);
        const stopNote = document.createElement('div');
        stopNote.className = 'message-source';
        stopNote.innerHTML = '<i class="bi bi-stop-circle"></i> Generation stopped';
        botBubble.parentElement.appendChild(stopNote);
      }
    } else {
      const errRow = createMessageRow('assistant', `⚠️ Error: ${err.message}`);
      messagesContainer.appendChild(errRow);
      scrollToBottom();
    }
  } finally {
    state.isStreaming = false;
    state.abortController = null;
    chatInput.disabled = false;
    chatInput.focus();
    _setStopMode(false);
  }
}

// ─── Stop Button ──────────────────────────────────────────────
sendBtn.addEventListener('click', () => {
  if (state.isStreaming) {
    // Stop mode — abort the request
    if (state.abortController) state.abortController.abort();
    return;
  }
  const text = chatInput.value.trim();
  if (text) {
    chatInput.value = '';
    chatInput.style.height = 'auto';
    updateSendBtn();
    sendMessage(text);
  }
});

// ─── Input handling ───────────────────────────────────────────
function updateSendBtn() {
  sendBtn.disabled = chatInput.value.trim() === '' || state.isStreaming;
}

chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, 140)}px`;
  updateSendBtn();
});

chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (state.isStreaming) return; // don't send while streaming (use Stop button)
    const text = chatInput.value.trim();
    if (text) {
      chatInput.value = '';
      chatInput.style.height = 'auto';
      updateSendBtn();
      sendMessage(text);
    }
  }
});

// ─── Starter Chips ────────────────────────────────────────────
document.querySelectorAll('.chip').forEach((chip) => {
  chip.addEventListener('click', () => { if (chip.dataset.msg) sendMessage(chip.dataset.msg); });
});

// ─── New Chat ─────────────────────────────────────────────────
newChatBtn.addEventListener('click', () => {
  if (state.abortController) { state.abortController.abort(); state.abortController = null; }
  state.hasMessages = false;
  messagesContainer.innerHTML = '';
  messagesContainer.style.display = 'none';
  welcomeScreen.style.display = '';
  _setStopMode(false);
  chatInput.disabled = false;
  chatInput.focus();
});

// ─── Language Selector ────────────────────────────────────────
langSelect.addEventListener('change', () => { state.language = langSelect.value; });

// ─── User Menu Toggle ─────────────────────────────────────────
userMenuBtn.addEventListener('click', () => { userMenuBtn.classList.toggle('open'); });

document.addEventListener('click', (e) => {
  if (!userMenuBtn.contains(e.target)) userMenuBtn.classList.remove('open');
});

// ─── Capability mode ──────────────────────────────────────────
document.querySelectorAll('.capability-item').forEach((item) => {
  item.addEventListener('click', () => {
    const mode = item.dataset.mode;
    if (mode === 'quiz')   { window.location.href = '/quiz.php';   return; }
    if (mode === 'scores') { window.location.href = '/scores.php'; return; }
    document.querySelectorAll('.capability-item').forEach((i) => i.classList.remove('active'));
    item.classList.add('active');
    if (mode === 'rag') chatInput.placeholder = 'Ask me about IPL teams, players, records...';
  });
});
