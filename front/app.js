'use strict';

const API_URL = 'http://localhost:8200/chat/api/v1';

const TOOL_META = {
  search_web:     { icon: '🔍', label: '웹 검색' },
  browse_url:     { icon: '🌐', label: 'URL 분석' },
  generate_image: { icon: '🎨', label: '이미지 생성' },
};
const DEFAULT_TOOL = { icon: '⚙️', label: '도구 실행' };

// ── 상태 ──────────────────────────────────────────────────────
let isStreaming   = false;
let citationMap   = {};   // index(number) → { title, url }
let currentBotEl  = null; // 현재 스트리밍 중인 봇 메시지 DOM
let accText       = '';   // 누적 텍스트
let cursorEl      = null; // 깜박이는 커서 DOM
let toolPanelEl   = null; // 현재 봇 메시지의 툴 패널 DOM

// ── 초기화 ────────────────────────────────────────────────────
const messagesArea = document.getElementById('messages-area');
const welcome      = document.getElementById('welcome');
const userInput    = document.getElementById('user-input');
const sendBtn      = document.getElementById('send-btn');
const headerStatus = document.getElementById('header-status');
const citeTooltip  = document.getElementById('cite-tooltip');
const citeTitle    = document.getElementById('cite-tooltip-title');
const citeUrl      = document.getElementById('cite-tooltip-url');

// 입력 높이 자동 조절
userInput.addEventListener('input', () => {
  userInput.style.height = 'auto';
  userInput.style.height = Math.min(userInput.scrollHeight, 160) + 'px';
  sendBtn.disabled = !userInput.value.trim() || isStreaming;
});

// Enter 전송 / Shift+Enter 줄바꿈
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendBtn.disabled) submit();
  }
});

sendBtn.addEventListener('click', submit);

document.getElementById('new-chat-btn').addEventListener('click', () => {
  if (isStreaming) return;
  messagesArea.innerHTML = '';
  messagesArea.appendChild(welcome);
  welcome.style.display = 'flex';
  citationMap = {};
  accText = '';
  currentBotEl = null;
  toolPanelEl = null;
});

// 추천 질문 칩
document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    userInput.value = chip.dataset.q;
    userInput.dispatchEvent(new Event('input'));
    submit();
  });
});

// ── 전송 ──────────────────────────────────────────────────────
async function submit() {
  const text = userInput.value.trim();
  if (!text || isStreaming) return;

  welcome.style.display = 'none';
  appendUserMessage(text);
  userInput.value = '';
  userInput.style.height = 'auto';
  sendBtn.disabled = true;

  // 봇 메시지 컨테이너 준비
  resetBotState();
  currentBotEl = createBotMessage();

  await streamChat(text);
}

// ── SSE 스트리밍 ───────────────────────────────────────────────
async function streamChat(userText) {
  isStreaming = true;
  setHeaderStatus('응답 생성 중...', 'running');

  try {
    const resp = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText , model_name : "gpt-4.1"}),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // 마지막 불완전한 줄 보관

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') { finalize(); return; }
        try { handleEvent(JSON.parse(raw)); } catch (_) {}
      }
    }
    finalize();

  } catch (err) {
    showBotError(`연결 오류: ${err.message}`);
    finalize();
  }
}

// ── 이벤트 라우터 ─────────────────────────────────────────────
function handleEvent(ev) {
  switch (ev.type) {

    // ── LLM 텍스트 델타
    case 'response.output_text.delta':
      appendTextDelta(ev.delta ?? '');
      break;

    // ── 툴 시작 배너
    case 'tools.start':
      toolPanelEl = createToolPanel(ev.tools);
      setHeaderStatus(`도구 실행 중 (${ev.tools.length}개)`, 'running');
      break;

    // ── 개별 툴 실행 중
    case 'tool.executing':
      upsertToolItem(ev.name, ev.args, 'executing');
      break;

    // ── 개별 툴 완료
    case 'tool.done':
      upsertToolItem(ev.name, null, 'done');
      break;

    // ── 개별 툴 오류
    case 'tool.error':
      upsertToolItem(ev.name, null, 'error');
      break;

    // ── 인용 메타 수신
    case 'citations.ready':
      citationMap = {};
      ev.citations.forEach(c => { citationMap[c.index] = c; });
      break;

    // ── 최종 토큰 사용량
    case 'usage.final':
      showUsage(ev.usage, ev.iterations);
      break;

    // ── 스트리밍 완료
    case 'stream.done':
      setToolPanelDone();
      break;

    // ── 서버 오류
    case 'stream.error':
      showBotError(ev.message);
      break;
  }
}

// ── 텍스트 델타 추가 ──────────────────────────────────────────
function appendTextDelta(delta) {
  accText += delta;
  const textEl = currentBotEl.querySelector('.bot-text');
  // 커서 임시 제거 후 텍스트 업데이트
  if (cursorEl && cursorEl.parentNode) cursorEl.remove();
  textEl.innerHTML = escapeToHtml(accText);
  // 커서 다시 추가
  textEl.appendChild(cursorEl);
  scrollToBottom();
}

// ── 최종 렌더링 ───────────────────────────────────────────────
function finalize() {
  isStreaming = false;

  // 커서 제거
  if (cursorEl && cursorEl.parentNode) cursorEl.remove();

  // 이 메시지 전용 citations 스냅샷 — 이후 전역 citationMap이 초기화돼도 유지됨
  const frozenCitations = { ...citationMap };

  // 마크다운 + 인용 렌더링
  if (currentBotEl) {
    const textEl = currentBotEl.querySelector('.bot-text');
    textEl.innerHTML = renderMarkdownWithCitations(accText);
    attachCitationListeners(textEl, frozenCitations);
  }

  setHeaderStatus('', '');
  sendBtn.disabled = !userInput.value.trim();
  scrollToBottom();
}

// ── 마크다운 + 인용 렌더링 ────────────────────────────────────
function renderMarkdownWithCitations(text) {
  let html = simpleMarkdown(text);
  // [N] → 클릭 가능한 cite-btn
  html = html.replace(/\[(\d+)\]/g, (match, n) => {
    const idx = parseInt(n, 10);
    return `<button class="cite-btn" data-index="${idx}">${match}</button>`;
  });
  return html;
}

// 가볍고 빠른 마크다운 변환 (외부 라이브러리 없이)
function simpleMarkdown(text) {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return escaped
    // 코드 블록 (```...```)
    .replace(/```[\w]*\n?([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // 인라인 코드
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // ### 헤더
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    // ## 헤더
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    // hr
    .replace(/^---$/gm, '<hr>')
    // bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // unordered list
    .replace(/^[*\-] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    // 단락 (빈 줄 기준)
    .split(/\n{2,}/)
    .map(block => {
      if (/^<(h[23]|ul|ol|pre|hr)/.test(block.trim())) return block;
      return `<p>${block.replace(/\n/g, '<br>')}</p>`;
    })
    .join('\n');
}

function escapeToHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
}

// ── 인용 툴팁 이벤트 연결 ─────────────────────────────────────
// citations: 이 메시지 전용 스냅샷 — 전역 citationMap과 독립적
function attachCitationListeners(container, citations) {
  container.querySelectorAll('.cite-btn').forEach(btn => {
    btn.addEventListener('mouseenter', (e) => showCiteTooltip(e, citations));
    btn.addEventListener('mouseleave', hideCiteTooltip);
    btn.addEventListener('click', () => {
      const cite = citations[parseInt(btn.dataset.index, 10)];
      if (cite?.url) window.open(cite.url, '_blank', 'noopener');
    });
  });
}

function showCiteTooltip(e, citations) {
  const idx  = parseInt(e.currentTarget.dataset.index, 10);
  const cite = citations[idx];
  if (!cite) return;

  citeTitle.textContent = cite.title || `출처 [${idx}]`;
  citeUrl.textContent   = cite.url   || '';
  citeUrl.href          = cite.url   || '#';

  const rect = e.currentTarget.getBoundingClientRect();
  citeTooltip.style.left = `${rect.left}px`;
  citeTooltip.style.top  = `${rect.top - citeTooltip.offsetHeight - 8}px`;
  citeTooltip.classList.add('visible');

  // 화면 밖으로 나가지 않게 보정 (렌더 후)
  requestAnimationFrame(() => {
    const tw = citeTooltip.offsetWidth;
    const left = Math.min(rect.left, window.innerWidth - tw - 16);
    citeTooltip.style.left = `${Math.max(8, left)}px`;
    const th = citeTooltip.offsetHeight;
    const top = rect.top - th - 8 < 8 ? rect.bottom + 8 : rect.top - th - 8;
    citeTooltip.style.top = `${top}px`;
  });
}

function hideCiteTooltip() {
  citeTooltip.classList.remove('visible');
}

// ── 툴 패널 ───────────────────────────────────────────────────
function createToolPanel(toolNames) {
  const panel = document.createElement('div');
  panel.className = 'tool-panel';
  panel.innerHTML = `
    <div class="tool-panel-header">
      <span class="ph-icon">⚙️</span>
      <span class="ph-label">도구 실행 중...</span>
      <span class="ph-toggle">▼</span>
    </div>
    <div class="tool-list"></div>`;

  panel.querySelector('.tool-panel-header').addEventListener('click', () => {
    panel.classList.toggle('collapsed');
  });

  const bubble = currentBotEl.querySelector('.bubble');
  bubble.insertBefore(panel, bubble.querySelector('.bot-text'));
  return panel;
}

function upsertToolItem(name, args, status) {
  if (!toolPanelEl) return;
  const list = toolPanelEl.querySelector('.tool-list');
  const meta = TOOL_META[name] ?? DEFAULT_TOOL;

  let item = list.querySelector(`[data-tool="${name}"]`);
  if (!item) {
    item = document.createElement('div');
    item.className = 'tool-item';
    item.dataset.tool = name;
    item.innerHTML = `
      <div class="tool-icon-wrap">${meta.icon}</div>
      <div class="tool-info">
        <div class="tool-name">${meta.label}</div>
        <div class="tool-args"></div>
      </div>
      <div class="tool-status"></div>`;
    list.appendChild(item);
  }

  // args 표시
  if (args) {
    const argsStr = Object.entries(args).map(([k, v]) => `${k}: "${v}"`).join(', ');
    item.querySelector('.tool-args').textContent = argsStr;
  }

  // 상태 아이콘
  const statusEl = item.querySelector('.tool-status');
  if (status === 'executing') {
    statusEl.innerHTML = '<div class="spinner"></div>';
  } else if (status === 'done') {
    statusEl.innerHTML = '<span class="status-done">✓</span>';
  } else if (status === 'error') {
    statusEl.innerHTML = '<span class="status-error">✗</span>';
  }
}

function setToolPanelDone() {
  if (!toolPanelEl) return;
  const label = toolPanelEl.querySelector('.ph-label');
  if (label) label.textContent = '도구 실행 완료';
}

// ── DOM 헬퍼 ──────────────────────────────────────────────────
function appendUserMessage(text) {
  const el = document.createElement('div');
  el.className = 'message user';
  el.innerHTML = `
    <div class="msg-row">
      <div class="bubble">${escapeToHtml(text)}</div>
      <div class="avatar user">나</div>
    </div>`;
  messagesArea.appendChild(el);
  scrollToBottom();
}

function createBotMessage() {
  const el = document.createElement('div');
  el.className = 'message bot';
  el.innerHTML = `
    <div class="msg-row">
      <div class="avatar bot">◈</div>
      <div class="bubble">
        <div class="bot-text"></div>
      </div>
    </div>`;

  cursorEl = document.createElement('span');
  cursorEl.className = 'cursor';
  el.querySelector('.bot-text').appendChild(cursorEl);

  messagesArea.appendChild(el);
  scrollToBottom();
  return el;
}

function showBotError(msg) {
  if (!currentBotEl) return;
  const bubble = currentBotEl.querySelector('.bubble');
  const errEl = document.createElement('div');
  errEl.className = 'error-msg';
  errEl.textContent = msg;
  bubble.appendChild(errEl);
}

function resetBotState() {
  citationMap  = {};
  accText      = '';
  cursorEl     = null;
  toolPanelEl  = null;
  currentBotEl = null;
}

function setHeaderStatus(text, state) {
  headerStatus.textContent = text;
  headerStatus.style.color = state === 'running' ? 'var(--accent)' : 'var(--text-muted)';
}

function scrollToBottom() {
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

// ── 토큰 사용량 표시 ──────────────────────────────────────────
function showUsage(usage, iterations) {
  if (!currentBotEl) return;
  const el = document.createElement('div');
  el.className = 'usage-bar';
  el.innerHTML = `
    <span class="usage-item">🔢 총 <strong>${usage.total_tokens.toLocaleString()}</strong> 토큰</span>
    <span class="usage-sep">·</span>
    <span class="usage-item">입력 <strong>${usage.input_tokens.toLocaleString()}</strong></span>
    <span class="usage-sep">·</span>
    <span class="usage-item">출력 <strong>${usage.output_tokens.toLocaleString()}</strong></span>
    <span class="usage-sep">·</span>
    <span class="usage-item">LLM 호출 <strong>${iterations}</strong>회</span>`;
  currentBotEl.querySelector('.bubble').appendChild(el);
}
