'use strict';

const API_URL = 'http://localhost:8200/chat/api/v1';
const MODEL_OPTIONS = ['gpt-4.1', 'gpt-5-chat-latest'];
const DEFAULT_MODEL = 'gpt-4.1';

const TOOL_META = {
  search_web:              { icon: '🔍', label: '웹 검색' },
  browse_url:              { icon: '🌐', label: 'URL 분석' },
  generate_image:          { icon: '🎨', label: '이미지 생성' },
  // korea-store-mcp (다이소/올리브영/CU/이마트24/메가박스/롯데시네마/CGV)
  daiso_search_products:   { icon: '🛒', label: '다이소 제품 검색' },
  daiso_find_stores:       { icon: '📍', label: '다이소 매장 검색' },
  daiso_check_inventory:   { icon: '📦', label: '다이소 재고 확인' },
  daiso_get_price_info:    { icon: '💰', label: '다이소 가격 조회' },
  daiso_get_display_location: { icon: '🗺️', label: '다이소 진열 위치' },
  cu_find_nearby_stores:   { icon: '🏪', label: 'CU 매장 검색' },
  cu_check_inventory:      { icon: '📦', label: 'CU 재고 확인' },
  emart24_find_nearby_stores: { icon: '🏪', label: '이마트24 매장 검색' },
  emart24_search_products: { icon: '🛒', label: '이마트24 상품 검색' },
  emart24_check_inventory: { icon: '📦', label: '이마트24 재고 확인' },
  megabox_find_nearby_theaters: { icon: '🎬', label: '메가박스 지점 검색' },
  megabox_list_now_showing:     { icon: '🎬', label: '메가박스 상영작 조회' },
  megabox_get_remaining_seats:  { icon: '💺', label: '메가박스 잔여석 조회' },
  lottecinema_find_nearby_theaters: { icon: '🎬', label: '롯데시네마 지점 검색' },
  lottecinema_list_now_showing:     { icon: '🎬', label: '롯데시네마 상영작 조회' },
  lottecinema_get_remaining_seats:  { icon: '💺', label: '롯데시네마 잔여석 조회' },
  cgv_find_theaters:       { icon: '🎬', label: 'CGV 극장 검색' },
  cgv_search_movies:       { icon: '🎬', label: 'CGV 상영작 조회' },
  cgv_get_timetable:       { icon: '🕐', label: 'CGV 시간표 조회' },
  oliveyoung_find_nearby_stores: { icon: '💄', label: '올리브영 매장 검색' },
  oliveyoung_check_inventory:    { icon: '📦', label: '올리브영 재고 확인' },
};
const DEFAULT_TOOL = { icon: '⚙️', label: '도구 실행' };

// ── 상태 ──────────────────────────────────────────────────────
let isStreaming   = false;
let isHILPending  = false; // HIL 선택 대기 중 — finalize 에서 isStreaming 유지
let citationMap   = {};   // index(number) → { title, url }
let currentBotEl  = null; // 현재 스트리밍 중인 봇 메시지 DOM
let accText       = '';   // 누적 텍스트
let cursorEl      = null; // 깜박이는 커서 DOM
let toolPanelEl   = null; // 현재 봇 메시지의 툴 패널 DOM

// ── 초기화 ────────────────────────────────────────────────────
const appRoot      = document.getElementById('app');
const sidebar      = document.getElementById('sidebar');
const sidebarBtn   = document.getElementById('sidebar-toggle');
const themeBtn     = document.getElementById('theme-toggle');
const toastEl      = document.getElementById('toast');

const messagesArea = document.getElementById('messages-area');
const welcome      = document.getElementById('welcome');
const userInput    = document.getElementById('user-input');
const sendBtn      = document.getElementById('send-btn');

const headerStatus = document.getElementById('header-status');
const statusDot    = document.getElementById('status-dot');
const modelBadge   = document.getElementById('model-badge');
const modelSelect  = document.getElementById('model-select');

const citeTooltip  = document.getElementById('cite-tooltip');
const citeTitle    = document.getElementById('cite-tooltip-title');
const citeUrl      = document.getElementById('cite-tooltip-url');

function getStoredModel() {
  const stored = localStorage.getItem('selected_model') || '';
  return MODEL_OPTIONS.includes(stored) ? stored : DEFAULT_MODEL;
}

function updateModelUI(model) {
  if (modelSelect) modelSelect.value = model;
  if (modelBadge) modelBadge.textContent = model;
}

function setSelectedModel(model, { silent = false } = {}) {
  const safeModel = MODEL_OPTIONS.includes(model) ? model : DEFAULT_MODEL;
  localStorage.setItem('selected_model', safeModel);
  updateModelUI(safeModel);
  if (!silent) showToast(`모델이 ${safeModel}로 변경되었습니다`);
  return safeModel;
}

function getSelectedModel() {
  return getStoredModel();
}

// ── UI: Theme ────────────────────────────────────────────────
function getStoredTheme() {
  return localStorage.getItem('theme') || '';
}
function applyTheme(theme) {
  // theme: 'light' | 'dark'
  if (theme === 'light') document.documentElement.dataset.theme = 'light';
  else document.documentElement.dataset.theme = 'dark';
  localStorage.setItem('theme', theme);
}
(function initTheme() {
  const stored = getStoredTheme();
  if (stored === 'light' || stored === 'dark') {
    applyTheme(stored);
    return;
  }
  // Prefer system if nothing stored
  const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
  applyTheme(prefersLight ? 'light' : 'dark');
})();

updateModelUI(getSelectedModel());
modelSelect?.addEventListener('change', (e) => {
  setSelectedModel(e.target.value);
});

themeBtn?.addEventListener('click', () => {
  const cur = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
  applyTheme(cur === 'light' ? 'dark' : 'light');
  showToast(cur === 'light' ? '다크 모드' : '라이트 모드');
});

// ── UI: Sidebar (mobile) ─────────────────────────────────────
function openSidebar() {
  sidebar.classList.add('open');
  appRoot.classList.add('sidebar-open');
}
function closeSidebar() {
  sidebar.classList.remove('open');
  appRoot.classList.remove('sidebar-open');
}
sidebarBtn?.addEventListener('click', () => {
  if (sidebar.classList.contains('open')) closeSidebar();
  else openSidebar();
});
// overlay click (pseudo element) – capture with root click
appRoot.addEventListener('click', (e) => {
  if (!appRoot.classList.contains('sidebar-open')) return;
  // If click is outside sidebar while open, close
  const inside = sidebar.contains(e.target) || sidebarBtn.contains(e.target);
  if (!inside) closeSidebar();
});

// ── 입력 높이 자동 조절 ───────────────────────────────────────
userInput.addEventListener('input', () => {
  userInput.style.height = 'auto';
  userInput.style.height = Math.min(userInput.scrollHeight, 180) + 'px';
  sendBtn.disabled = !userInput.value.trim() || isStreaming;
});

// Enter 전송 / Shift+Enter 줄바꿈 / Ctrl+Enter 전송
userInput.addEventListener('keydown', (e) => {
  const isEnter = e.key === 'Enter';
  const isCtrlEnter = isEnter && (e.ctrlKey || e.metaKey);
  if ((isEnter && !e.shiftKey) || isCtrlEnter) {
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
  setHeaderStatus('', '');
  showToast('새 대화가 시작되었습니다');
  closeSidebar();
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

  // 모바일에서 보내면 sidebar 닫기
  closeSidebar();

  // 봇 메시지 컨테이너 준비
  resetBotState();
  currentBotEl = createBotMessage();

  await streamChat(text);
}

// ── SSE 스트리밍 ───────────────────────────────────────────────
async function streamChat(userText) {
  isStreaming = true;
  setHeaderStatus('응답 생성 중…', 'running');

  try {
    const resp = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText, model_name: getSelectedModel() }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

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
    setHeaderStatus('연결 오류', 'error');
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

    // ── 툴 시작 배너 (중복 호출 시 패널을 새로 만들지 않고 기존 패널 재사용)
    case 'tools.start':
      if (!toolPanelEl) {
        toolPanelEl = createToolPanel(ev.tools);
      }
      setHeaderStatus('도구 실행 중…', 'running');
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
      setHeaderStatus('오류', 'error');
      break;

    // ── Human-in-the-Loop: 사용자 선택 필요
    case 'human_input.required':
      isHILPending = true;
      showHumanInputUI(ev.session_id, ev.question, ev.options);
      setHeaderStatus('선택 대기 중…', 'running');
      break;

    case 'image_preview':
      renderImagePreview(ev.b64);
      break;

    case 'image_final':
      renderImageFinal(ev.b64);
      break;
  }
}

// ── 이미지 미리보기 렌더링 ─────────────────────────────────────
let previewImgEl = null;

function renderImagePreview(b64) {
  if (!currentBotEl) return;

  const bubble = currentBotEl.querySelector('.bubble');

  if (!previewImgEl) {
    previewImgEl = document.createElement('img');
    previewImgEl.className = 'gen-image preview';
    bubble.appendChild(previewImgEl);
  }

  previewImgEl.src = 'data:image/png;base64,' + b64;
  scrollToBottom();
}

function renderImageFinal(b64) {
  if (!currentBotEl) return;

  const bubble = currentBotEl.querySelector('.bubble');

  const finalImg = document.createElement('img');
  finalImg.className = 'gen-image final';
  finalImg.src = 'data:image/png;base64,' + b64;

  if (previewImgEl && previewImgEl.parentNode) {
    previewImgEl.replaceWith(finalImg);
    previewImgEl = null;
  } else {
    bubble.appendChild(finalImg);
  }

  scrollToBottom();
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
  // HIL 대기 중이면 isStreaming 유지 (전송 버튼 비활성 유지)
  if (!isHILPending) {
    isStreaming = false;
    sendBtn.disabled = !userInput.value.trim();
  }

  // 커서 제거
  if (cursorEl && cursorEl.parentNode) cursorEl.remove();

  // 이 메시지 전용 citations 스냅샷 — 이후 전역 citationMap이 초기화돼도 유지됨
  const frozenCitations = { ...citationMap };

  // 마크다운 + 인용 렌더링
  if (currentBotEl) {
    const textEl = currentBotEl.querySelector('.bot-text');
    textEl.innerHTML = renderMarkdownWithCitations(accText);
    attachCitationListeners(textEl, frozenCitations);
    enhanceCodeBlocks(textEl);
  }

  if (!isHILPending) setHeaderStatus('', '');
  scrollToBottom();
}

// ── 마크다운 + 인용 렌더링 ────────────────────────────────────
function renderMarkdownWithCitations(text) {
  let html = simpleMarkdown(text);
  // [N] → 클릭 가능한 cite-btn
  html = html.replace(/\[(\d+)\]/g, (match, n) => {
    const idx = parseInt(n, 10);
    return `<button class="cite-btn" data-index="${idx}" type="button">${match}</button>`;
  });
  return html;
}

// 가볍고 빠른 마크다운 변환 (외부 라이브러리 없이)
function simpleMarkdown(text) {
  // ① 이미지 플레이스홀더 추출
  const images = [];
  text = text.replace(/!\[([^\]]*)\]\((https?:\/\/[^\)]+)\)/g, (_, alt, url) => {
    images.push(`<img class="md-img" src="${url}" alt="${alt}" loading="lazy">`);
    return `\x00IMG${images.length - 1}\x00`;
  });

  // ② HTML escape
  text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // ③ 코드 블록 보호
  const codes = [];
  text = text.replace(/```[\w]*\n?([\s\S]*?)```/g, (_, c) => {
    codes.push(c);
    return `\x00CODE${codes.length - 1}\x00`;
  });

  // ④ 인라인 변환 헬퍼
  const inline = s => s
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<!\d)\*(?!\d)([^*\n]+?)(?<!\d)\*(?!\d)/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // ⑤ 테이블 헬퍼
  const parseTable = lines => {
    if (lines.length < 2) return null;
    const cells = row => row.split('|').slice(1, -1).map(c => c.trim());
    const sepCells = cells(lines[1]);
    if (!sepCells.every(c => /^:?-+:?$/.test(c))) return null;
    const aligns = sepCells.map(c => /^:-+:$/.test(c) ? 'center' : /^-+:$/.test(c) ? 'right' : 'left');
    const ths = cells(lines[0]).map((h, i) => `<th style="text-align:${aligns[i]}">${inline(h)}</th>`).join('');
    const trs = lines.slice(2)
      .map(r => '<tr>' + cells(r).map((c, i) => `<td style="text-align:${aligns[i]}">${inline(c)}</td>`).join('') + '</tr>')
      .join('');
    return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
  };

  // ⑥ 줄 단위 블록 처리 (표 · 비순서 목록 · 순서 목록)
  const out = [];
  const lines = text.split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // 표: 현재 줄이 | 로 시작하고 다음 줄이 구분자 행
    if (line.startsWith('|') && i + 1 < lines.length && /^\|[-: |]+\|/.test(lines[i + 1])) {
      const tLines = [];
      while (i < lines.length && lines[i].startsWith('|')) tLines.push(lines[i++]);
      out.push(parseTable(tLines) ?? tLines.join('\n'));
      continue;
    }

    // 비순서 목록 (- 또는 *)
    if (/^[*\-] /.test(line)) {
      const items = [];
      while (i < lines.length && /^[*\-] /.test(lines[i]))
        items.push(`<li>${inline(lines[i++].replace(/^[*\-] /, ''))}</li>`);
      out.push(`<ul>${items.join('')}</ul>`);
      continue;
    }

    // 순서 목록 (1. 2. …)
    if (/^\d+\. /.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\. /.test(lines[i]))
        items.push(`<li>${inline(lines[i++].replace(/^\d+\. /, ''))}</li>`);
      out.push(`<ol>${items.join('')}</ol>`);
      continue;
    }

    out.push(line);
    i++;
  }
  text = out.join('\n');

  // ⑦ 헤더(h1~h6) · 수평선
  text = text
    .replace(/^###### (.+)$/gm, (_, c) => `<h6>${inline(c)}</h6>`)
    .replace(/^##### (.+)$/gm,  (_, c) => `<h5>${inline(c)}</h5>`)
    .replace(/^#### (.+)$/gm,   (_, c) => `<h4>${inline(c)}</h4>`)
    .replace(/^### (.+)$/gm,    (_, c) => `<h3>${inline(c)}</h3>`)
    .replace(/^## (.+)$/gm,     (_, c) => `<h2>${inline(c)}</h2>`)
    .replace(/^# (.+)$/gm,      (_, c) => `<h1>${inline(c)}</h1>`)
    .replace(/^---$/gm, '<hr>');

  // ⑧ 나머지 인라인 변환 (일반 텍스트 / 헤더 내부 미처리분)
  text = inline(text);

  // ⑨ 단락 분리 (빈 줄 기준)
  return text
    .split(/\n{2,}/)
    .map(block => {
      const t = block.trim();
      if (!t) return '';
      if (/^<(h[1-6]|ul|ol|pre|hr|table)/.test(t)) return t;
      if (t.startsWith('\x00CODE')) return t;
      return `<p>${block.replace(/\n/g, '<br>')}</p>`;
    })
    .filter(Boolean)
    .join('\n')
    .replace(/\x00CODE(\d+)\x00/g, (_, n) => `<pre><code>${codes[+n]}</code></pre>`)
    .replace(/\x00IMG(\d+)\x00/g,  (_, n) => images[+n]);
}

function escapeToHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
}

// ── Code block UX (copy button) ─────────────────────────────
function enhanceCodeBlocks(container) {
  const pres = container.querySelectorAll('pre');
  pres.forEach(pre => {
    // Avoid duplicate
    if (pre.querySelector('.code-copy')) return;

    const btn = document.createElement('button');
    btn.className = 'code-copy';
    btn.type = 'button';
    btn.textContent = '복사';
    btn.addEventListener('click', async () => {
      try {
        const code = pre.querySelector('code')?.textContent ?? pre.textContent;
        await navigator.clipboard.writeText(code);
        btn.textContent = '복사됨';
        showToast('코드가 복사되었습니다');
        setTimeout(() => (btn.textContent = '복사'), 1200);
      } catch (_) {
        showToast('복사 권한이 없습니다');
      }
    });
    pre.appendChild(btn);
  });
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

// ── Toast ───────────────────────────────────────────────────
let toastTimer = null;
function showToast(msg) {
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), 1400);
}

// ── 툴 패널 ───────────────────────────────────────────────────
function createToolPanel() {
  const panel = document.createElement('div');
  panel.className = 'tool-panel';
  panel.innerHTML = `
    <div class="tool-panel-header">
      <span class="ph-icon">⚙️</span>
      <span class="ph-label">도구 실행 중…</span>
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
      <div class="avatar user" title="나">나</div>
    </div>`;
  messagesArea.appendChild(el);
  scrollToBottom();
}

function createBotMessage() {
  const el = document.createElement('div');
  el.className = 'message bot';
  el.innerHTML = `
    <div class="msg-row">
      <div class="avatar bot" title="Assistant">◈</div>
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
  isHILPending = false;
  citationMap  = {};
  accText      = '';
  cursorEl     = null;
  toolPanelEl  = null;
  currentBotEl = null;
}

function setHeaderStatus(text, state) {
  headerStatus.textContent = text || '';
  statusDot.classList.remove('running', 'error');
  if (state === 'running') statusDot.classList.add('running');
  if (state === 'error') statusDot.classList.add('error');
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

// ── Model badge / selector sync ───────────────────────────────
try {
  setSelectedModel(getSelectedModel(), { silent: true });
} catch (_) {}

// ── Human-in-the-Loop UI ──────────────────────────────────────
function showHumanInputUI(sessionId, question, options) {
  if (!currentBotEl) return;
  const bubble = currentBotEl.querySelector('.bubble');

  const panel = document.createElement('div');
  panel.className = 'hitl-panel';
  panel.innerHTML = `
    <div class="hitl-question">${escapeToHtml(question)}</div>
    <div class="hitl-options">
      ${options.map(opt =>
        `<button class="hitl-option-btn" type="button">${escapeToHtml(opt)}</button>`
      ).join('')}
    </div>`;

  bubble.appendChild(panel);
  scrollToBottom();

  panel.querySelectorAll('.hitl-option-btn').forEach((btn, idx) => {
    btn.addEventListener('click', () => {
      const choice = options[idx];

      // 버튼 비활성화 + 선택 표시
      panel.querySelectorAll('.hitl-option-btn').forEach(b => { b.disabled = true; });
      btn.classList.add('selected');

      // 패널을 "선택됨" 뱃지로 교체
      const badge = document.createElement('div');
      badge.className = 'hitl-selected';
      badge.textContent = `✓ ${choice} 선택됨`;
      panel.replaceWith(badge);

      resumeStream(sessionId, choice);
    });
  });
}

async function resumeStream(sessionId, choice) {
  isHILPending = false;
  isStreaming   = true;
  setHeaderStatus('응답 생성 중…', 'running');

  // 기존 bot 메시지에 이어서 커서 복원
  const textEl = currentBotEl.querySelector('.bot-text');
  cursorEl = document.createElement('span');
  cursorEl.className = 'cursor';
  textEl.appendChild(cursorEl);

  try {
    const resp = await fetch(`${API_URL}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, choice }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') { finalize(); return; }
        try { handleEvent(JSON.parse(raw)); } catch (_) {}
      }
    }
    finalize();

  } catch (err) {
    showBotError(`재개 오류: ${err.message}`);
    finalize();
  }
}
