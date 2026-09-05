/**
 * JARVIS AI — QUANTUM LIVE HUD CLIENT (v2.5)
 * Executive Multi-Agent Voice & Vision Interface
 * 60 FPS HTML5 Canvas Visualizer, Waveform Soundwave, Push-To-Talk,
 * Responsive Layout Modes, Settings Deck, Memory Bank & Vision Lightbox.
 */

(() => {
  // ── DOM References ────────────────────────────────────────────────────────
  // Canvas & Core
  const canvas = document.getElementById('quantumCanvas');
  const ctx = canvas.getContext('2d');
  const quantumCore = document.getElementById('quantumCore');
  const coreEmitter = document.getElementById('coreEmitter');
  const coreProtocolText = document.getElementById('coreProtocolText');
  const stateIndicatorBadge = document.getElementById('stateIndicatorBadge');
  const stateText = document.getElementById('stateText');
  const stateDot = document.getElementById('stateDot');

  // Mode Controller
  const modeContinuousBtn = document.getElementById('modeContinuousBtn');
  const modeWakewordBtn = document.getElementById('modeWakewordBtn');
  const modePttBtn = document.getElementById('modePttBtn');

  // Waveform Soundwave & Telemetry
  const waveformBarsContainer = document.getElementById('waveformBarsContainer');
  const energyMeterVal = document.getElementById('energyMeterVal');
  const thresholdIndicator = document.getElementById('thresholdIndicator');
  const modelBadge = document.getElementById('modelBadge');
  const cpuVal = document.getElementById('cpuVal');
  const ramVal = document.getElementById('ramVal');
  const cpuMeterBar = document.getElementById('cpuMeterBar');
  const ramMeterBar = document.getElementById('ramMeterBar');
  const micDeviceName = document.getElementById('micDeviceName');

  // View Switcher
  const hudWorkspace = document.getElementById('hudWorkspace');
  const viewSplitBtn = document.getElementById('viewSplitBtn');
  const viewChatBtn = document.getElementById('viewChatBtn');
  const viewHudBtn = document.getElementById('viewHudBtn');

  // Header Actions
  const voiceOutputToggleBtn = document.getElementById('voiceOutputToggleBtn');
  const voiceSvg = document.getElementById('voiceSvg');
  const voiceBtnLabel = document.getElementById('voiceBtnLabel');
  const micToggleBtn = document.getElementById('micToggleBtn');
  const micSvg = document.getElementById('micSvg');
  const micBtnLabel = document.getElementById('micBtnLabel');
  const openSettingsBtn = document.getElementById('openSettingsBtn');
  const openMemoryBtn = document.getElementById('openMemoryBtn');

  // Conversation Feed
  const messagesContainer = document.getElementById('messagesContainer');
  const typingIndicator = document.getElementById('typingIndicator');
  const typingText = document.getElementById('typingText');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const initTime = document.getElementById('initTime');

  // Bottom Floating Input Deck
  const speakingBargeBar = document.getElementById('speakingBargeBar');
  const haltSpeechBtn = document.getElementById('haltSpeechBtn');
  const deckMicBtn = document.getElementById('deckMicBtn');
  const deckMicSvg = document.getElementById('deckMicSvg');
  const pttTriggerBtn = document.getElementById('pttTriggerBtn');
  const pttBtnText = document.getElementById('pttBtnText');
  const browserMicBtn = document.getElementById('browserMicBtn');
  const inputForm = document.getElementById('inputForm');
  const textInputField = document.getElementById('textInputField');

  // Settings Modal
  const settingsModalBackdrop = document.getElementById('settingsModalBackdrop');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  const themeCards = document.querySelectorAll('.theme-card');
  const voicePersonaSelect = document.getElementById('voicePersonaSelect');
  const speechRateRange = document.getElementById('speechRateRange');
  const speechRateVal = document.getElementById('speechRateVal');
  const sfxToggleBtn = document.getElementById('sfxToggleBtn');
  const testChimeBtn = document.getElementById('testChimeBtn');
  const vadThresholdRange = document.getElementById('vadThresholdRange');
  const vadThresholdVal = document.getElementById('vadThresholdVal');

  // Memory Drawer
  const memoryDrawer = document.getElementById('memoryDrawer');
  const drawerScrim = document.getElementById('drawerScrim');
  const closeMemoryBtn = document.getElementById('closeMemoryBtn');
  const tabMemoriesBtn = document.getElementById('tabMemoriesBtn');
  const tabToolsBtn = document.getElementById('tabToolsBtn');
  const paneMemories = document.getElementById('paneMemories');
  const paneTools = document.getElementById('paneTools');
  const memoryList = document.getElementById('memoryList');
  const memorySearchInput = document.getElementById('memorySearchInput');
  const toolsGrid = document.getElementById('toolsGrid');

  // Lightbox Modal
  const lightboxModal = document.getElementById('lightboxModal');
  const lightboxImg = document.getElementById('lightboxImg');
  const lightboxTitle = document.getElementById('lightboxTitle');
  const lightboxDownloadBtn = document.getElementById('lightboxDownloadBtn');
  const closeLightboxBtn = document.getElementById('closeLightboxBtn');

  // Toast Container
  const toastPod = document.getElementById('toastPod');

  if (initTime) {
    initTime.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // ── State Variables ───────────────────────────────────────────────────────
  let ws = null;
  let currentState = 'LISTENING';
  let targetEnergy = 0.0;
  let smoothEnergy = 0.0;
  let rawEnergy = 0.0;
  let threshold = 0.0025;
  let isMuted = false;
  let reconnectInterval = 1000;
  let voiceOutputEnabled = true;
  let selectedVoiceGender = 'male';
  let listeningMode = 'continuous';
  let sfxEnabled = true;
  let speechRateModifier = 0;
  let isPttHeld = false;
  let cachedMemories = [];

  // ── Initialize Real-Time Waveform Equalizer Bars ──────────────────────────
  const NUM_WAVE_BARS = 28;
  const waveBars = [];
  if (waveformBarsContainer) {
    waveformBarsContainer.innerHTML = '';
    for (let i = 0; i < NUM_WAVE_BARS; i++) {
      const bar = document.createElement('div');
      bar.className = 'wave-bar';
      waveformBarsContainer.appendChild(bar);
      waveBars.push(bar);
    }
  }

  // ── Web Audio Synthesizer (Sci-Fi Sound FX) ───────────────────────────────
  let audioCtx = null;
  function getAudioContext() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) audioCtx = new AudioContext();
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    return audioCtx;
  }

  function playActivationChime() {
    if (!sfxEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880.0, ctx.currentTime + 0.09); // A5

      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.12);
    } catch (e) {}
  }

  function playCompletionChime() {
    if (!sfxEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const now = ctx.currentTime;
      [659.25, 1046.5].forEach((freq) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now);
        gain.gain.setValueAtTime(0.06, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(now + 0.16);
      });
    } catch (e) {}
  }

  function playCancelChime() {
    if (!sfxEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(440.0, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(220.0, ctx.currentTime + 0.09);
      gain.gain.setValueAtTime(0.07, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.1);
    } catch (e) {}
  }

  // ── Toast Notifications ───────────────────────────────────────────────────
  function showToast(message, icon = '⚡') {
    if (!toastPod) return;
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
    toastPod.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 2400);
  }

  // ── Theme State & Setup ───────────────────────────────────────────────────
  let currentTheme = localStorage.getItem('jarvis_hud_theme') || 'theme-cyan';
  document.body.className = currentTheme;
  updateActiveThemeCard(currentTheme);

  function updateActiveThemeCard(themeName) {
    themeCards.forEach((card) => {
      if (card.getAttribute('data-theme') === themeName) {
        card.classList.add('active');
      } else {
        card.classList.remove('active');
      }
    });
  }

  function getThemeColors() {
    if (document.body.classList.contains('theme-crimson')) {
      return { primary: '#ff2a5f', secondary: '#ff7700', glow: 'rgba(255, 42, 95, 0.45)' };
    } else if (document.body.classList.contains('theme-emerald')) {
      return { primary: '#00ff88', secondary: '#00d2ff', glow: 'rgba(0, 255, 136, 0.45)' };
    } else if (document.body.classList.contains('theme-violet')) {
      return { primary: '#c084fc', secondary: '#9333ea', glow: 'rgba(192, 132, 252, 0.45)' };
    } else if (document.body.classList.contains('theme-obsidian')) {
      return { primary: '#e2e8f0', secondary: '#64748b', glow: 'rgba(226, 232, 240, 0.35)' };
    }
    return { primary: '#00f0ff', secondary: '#0088ff', glow: 'rgba(0, 240, 255, 0.45)' };
  }

  function getStatePalette(state) {
    const themeCol = getThemeColors();
    switch (state) {
      case 'HEARING':
        return { primary: '#10b981', secondary: '#059669', glow: 'rgba(16, 185, 129, 0.6)', label: 'HEARING SPEECH' };
      case 'THINKING':
      case 'PROCESSING':
        return { primary: '#f59e0b', secondary: '#d97706', glow: 'rgba(245, 158, 11, 0.6)', label: 'PROCESSING QUERY' };
      case 'SPEAKING':
        return { primary: '#a855f7', secondary: '#7c3aed', glow: 'rgba(168, 85, 247, 0.65)', label: 'JARVIS RESPONDING' };
      case 'MUTED':
        return { primary: '#ef4444', secondary: '#991b1b', glow: 'rgba(239, 68, 68, 0.45)', label: 'MIC MUTED' };
      case 'LISTENING':
      default:
        return {
          primary: themeCol.primary,
          secondary: themeCol.secondary,
          glow: themeCol.glow,
          label: listeningMode === 'ptt' ? 'PUSH-TO-TALK READY' : (listeningMode === 'wakeword' ? 'WAKE-WORD ONLY ("JARVIS")' : 'CONTINUOUS LISTENING'),
        };
    }
  }

  // ── WebSocket Connection Management ───────────────────────────────────────
  function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

    console.log('[HUD] Connecting to WebSocket:', wsUrl);
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[HUD] WebSocket connection established.');
      updateStatusBadge('SYSTEM ONLINE', true);
      reconnectInterval = 1000;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
      } catch (err) {
        console.error('[HUD] Error parsing WS payload:', err);
      }
    };

    ws.onclose = () => {
      console.warn('[HUD] WebSocket closed. Reconnecting in', reconnectInterval, 'ms...');
      updateStatusBadge('OFFLINE — RECONNECTING', false);
      setTimeout(connectWebSocket, reconnectInterval);
      reconnectInterval = Math.min(reconnectInterval * 1.5, 8000);
    };

    ws.onerror = (err) => {
      console.error('[HUD] WebSocket error:', err);
      updateStatusBadge('CONNECTION ERROR', false);
    };
  }

  // ── Dispatch Incoming Server Messages ─────────────────────────────────────
  function handleServerMessage(data) {
    switch (data.type) {
      case 'init':
        isMuted = data.is_muted;
        threshold = data.threshold || 0.0025;
        if (data.model && modelBadge) modelBadge.textContent = data.model;
        if (data.listening_mode) updateListeningModeUI(data.listening_mode);
        if (data.voice_gender) {
          selectedVoiceGender = data.voice_gender;
          if (voicePersonaSelect) voicePersonaSelect.value = selectedVoiceGender;
        }
        updateThresholdMarker(threshold);
        updateMicButtons();
        setAssistantState(data.state);
        break;

      case 'energy':
        targetEnergy = data.normalized;
        rawEnergy = data.raw;
        updateEnergySpectrum(targetEnergy, rawEnergy);
        break;

      case 'state':
        setAssistantState(data.state);
        break;

      case 'user_input':
        appendMessage('user', data.text, data.source);
        playActivationChime();
        break;

      case 'thinking':
        showTyping(data.text ? `Analyzing: "${data.text.slice(0, 32)}..."` : 'Jarvis is processing...');
        setAssistantState('THINKING');
        break;

      case 'routed':
        showTyping(`Engaging ${data.agent} Agent (${data.intent})...`);
        break;

      case 'response':
        hideTyping();
        appendMessage('assistant', data.text);
        setAssistantState('SPEAKING');
        // Note: Python backend Edge-TTS speaks cleanly through laptop speakers.
        // We do NOT trigger browser speechSynthesis here to avoid duplicate dual voice playback.
        break;

      case 'screenshot':
        appendScreenshotCard(data);
        break;

      case 'interrupted':
        console.log('[HUD] Speech interrupted by barge-in or stop.');
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        playCancelChime();
        hideTyping();
        setAssistantState('LISTENING');
        break;

      case 'telemetry':
        updateTelemetry(data);
        break;

      case 'mic_toggled':
        isMuted = data.is_muted;
        setAssistantState(data.state);
        updateMicButtons();
        break;

      case 'listening_mode_changed':
        updateListeningModeUI(data.mode);
        break;

      case 'speech_rate_changed':
        speechRateModifier = data.rate || 0;
        if (speechRateRange) speechRateRange.value = String(speechRateModifier);
        if (speechRateVal) speechRateVal.textContent = `${(1 + speechRateModifier / 100).toFixed(2)}x`;
        break;

      case 'voice_switched':
        selectedVoiceGender = data.gender;
        if (voicePersonaSelect) voicePersonaSelect.value = selectedVoiceGender;
        break;

      case 'memory_data':
        renderMemoryData(data.memories || [], data.tools || []);
        break;

      default:
        break;
    }
  }

  // ── State & UI Updaters ───────────────────────────────────────────────────
  function setAssistantState(state) {
    currentState = (state || 'LISTENING').toUpperCase();
    const pal = getStatePalette(currentState);

    if (stateText) stateText.textContent = pal.label;
    if (coreProtocolText) coreProtocolText.textContent = pal.label;
    if (stateIndicatorBadge) {
      stateIndicatorBadge.style.color = pal.primary;
      stateIndicatorBadge.style.borderColor = pal.primary;
      stateIndicatorBadge.style.background = `rgba(${parseInt(pal.primary.slice(1,3),16)}, ${parseInt(pal.primary.slice(3,5),16)}, ${parseInt(pal.primary.slice(5,7),16)}, 0.1)`;
    }
    if (stateDot) {
      stateDot.style.background = pal.primary;
      stateDot.style.boxShadow = `0 0 10px ${pal.primary}`;
    }

    // Toggle barge-in stop bar when Jarvis is speaking
    if (speakingBargeBar) {
      speakingBargeBar.style.display = (currentState === 'SPEAKING') ? 'flex' : 'none';
    }

    if (currentState === 'MUTED') {
      isMuted = true;
      updateMicButtons();
    } else if (isMuted && currentState !== 'MUTED') {
      isMuted = false;
      updateMicButtons();
    }
  }

  function updateStatusBadge(text, isOnline) {
    if (stateText) stateText.textContent = text;
    if (stateDot) {
      stateDot.style.background = isOnline ? 'var(--primary)' : 'var(--accent-red)';
      stateDot.style.boxShadow = isOnline ? '0 0 10px var(--primary)' : '0 0 10px var(--accent-red)';
    }
  }

  function updateTelemetry(data) {
    if (data.cpu !== undefined && cpuVal && cpuMeterBar) {
      const cpu = Math.round(data.cpu);
      cpuVal.textContent = `${cpu}%`;
      cpuMeterBar.style.width = `${cpu}%`;
    }
    if (data.ram !== undefined && ramVal && ramMeterBar) {
      const ram = Math.round(data.ram);
      ramVal.textContent = `${ram}%`;
      ramMeterBar.style.width = `${ram}%`;
    }
    if (data.model && modelBadge) {
      modelBadge.textContent = data.model;
    }
    if (data.mic_name && micDeviceName) {
      micDeviceName.textContent = data.mic_name;
    }
  }

  function updateEnergySpectrum(norm, raw) {
    if (energyMeterVal) energyMeterVal.textContent = raw.toFixed(5);

    // Animate equalizer soundwave bars
    const activeCount = Math.round(norm * NUM_WAVE_BARS);
    waveBars.forEach((bar, idx) => {
      if (idx <= activeCount) {
        bar.classList.add('active');
        const heightMult = Math.sin((idx / NUM_WAVE_BARS) * Math.PI);
        const dynamicH = Math.max(3, Math.round((norm * 20 + 2) * heightMult + Math.random() * 4));
        bar.style.height = `${dynamicH}px`;
      } else {
        bar.classList.remove('active');
        bar.style.height = '3px';
      }
    });

    if (norm > 0.15 && currentState === 'LISTENING') {
      setAssistantState('HEARING');
    }
  }

  function updateThresholdMarker(thresh) {
    if (!thresholdIndicator) return;
    const markerPct = Math.min(Math.max((thresh / 0.015) * 100, 5), 85);
    thresholdIndicator.style.left = `${markerPct}%`;
    if (vadThresholdRange) vadThresholdRange.value = String(thresh);
    if (vadThresholdVal) vadThresholdVal.textContent = thresh.toFixed(4);
  }

  function updateMicButtons() {
    if (isMuted) {
      if (micToggleBtn) micToggleBtn.className = 'action-icon-btn muted';
      if (micBtnLabel) micBtnLabel.textContent = 'Muted';
      if (deckMicBtn) deckMicBtn.className = 'deck-mic-button muted';
    } else {
      if (micToggleBtn) micToggleBtn.className = 'action-icon-btn active';
      if (micBtnLabel) micBtnLabel.textContent = 'Mic On';
      if (deckMicBtn) deckMicBtn.className = 'deck-mic-button active';
    }
  }

  function updateListeningModeUI(mode) {
    listeningMode = mode;
    [modeContinuousBtn, modeWakewordBtn, modePttBtn].forEach((btn) => {
      if (btn) btn.classList.remove('active');
    });

    if (mode === 'continuous' && modeContinuousBtn) modeContinuousBtn.classList.add('active');
    if (mode === 'wakeword' && modeWakewordBtn) modeWakewordBtn.classList.add('active');
    if (mode === 'ptt' && modePttBtn) modePttBtn.classList.add('active');

    if (mode === 'ptt') {
      document.body.classList.add('mode-ptt');
    } else {
      document.body.classList.remove('mode-ptt');
    }

    setAssistantState(currentState);
  }

  // ── Conversation Feed Rendering ───────────────────────────────────────────
  function appendMessage(sender, text, source = '') {
    if (!text || !text.trim()) return;

    const card = document.createElement('div');
    card.className = `message-card ${sender === 'user' ? 'user-msg' : 'assistant-msg'}`;

    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    let avatarHtml = '';
    let senderName = 'JARVIS CORE';
    let tagHtml = '';

    if (sender === 'user') {
      const isVoice = (source === 'voice');
      avatarHtml = `<div class="user-avatar-badge">${isVoice ? '🎙️' : '⌨️'}</div>`;
      senderName = 'YOU (SIR)';
      tagHtml = `<span class="tag-pill">${(source || 'INPUT').toUpperCase()}</span>`;
    } else {
      avatarHtml = `
        <div class="assistant-avatar-badge">
          <div class="avatar-glow"></div>
          <span class="avatar-initial">J</span>
        </div>
      `;

      if (text.includes("weather") || text.includes("temperature")) {
        tagHtml = '<span class="tag-pill tag-weather">WEATHER AGENT</span>';
      } else if (text.includes("opened") || text.includes("playing") || text.includes("app") || text.includes("Screenshot")) {
        tagHtml = '<span class="tag-pill tag-desktop">DESKTOP AGENT</span>';
      } else if (text.includes("CPU") || text.includes("system") || text.includes("status")) {
        tagHtml = '<span class="tag-pill tag-system">SYSTEM AGENT</span>';
      } else {
        tagHtml = '<span class="tag-pill">QUANTUM INTELLIGENCE</span>';
      }
    }

    card.innerHTML = `
      <div class="msg-avatar-wrap">${avatarHtml}</div>
      <div class="msg-content-wrap">
        <div class="msg-meta-row">
          <span class="sender-name">${senderName}</span>
          <span class="timestamp">${nowStr}</span>
          ${tagHtml}
        </div>
        <div class="msg-body-text">${renderFormattedMessage(text)}</div>
      </div>
    `;

    messagesContainer.appendChild(card);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function renderFormattedMessage(rawText) {
    if (!rawText) return '';

    let parsedHtml = '';
    if (window.marked) {
      try {
        marked.setOptions({
          gfm: true,
          breaks: true,
        });
        parsedHtml = marked.parse(rawText);
      } catch (e) {
        console.warn('Marked parse error:', e);
      }
    }

    if (!parsedHtml) {
      parsedHtml = escapeHtml(rawText)
        .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br/>');
    }

    // Wrap code blocks with executive header & 1-click Copy button
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = parsedHtml;

    tempDiv.querySelectorAll('pre').forEach((preElem) => {
      const codeElem = preElem.querySelector('code');
      const rawCode = codeElem ? codeElem.textContent : preElem.textContent;
      const langClass = codeElem ? (codeElem.className || '') : '';
      const langMatch = langClass.match(/language-([a-zA-Z0-9_\-+]+)/);
      const cleanLang = (langMatch ? langMatch[1] : 'CODE').toUpperCase();
      const blockId = 'code_' + Math.random().toString(36).substring(2, 9);

      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';
      wrapper.innerHTML = `
        <div class="code-block-header">
          <span class="code-lang-tag">⚡ ${cleanLang}</span>
          <button type="button" class="copy-code-btn" data-target="${blockId}" title="Copy code to clipboard">
            <span class="copy-text">Copy</span>
          </button>
        </div>
        <pre><code id="${blockId}" class="code-content">${escapeHtml(rawCode.trim())}</code></pre>
      `;
      preElem.parentNode.replaceChild(wrapper, preElem);
    });

    return tempDiv.innerHTML;
  }

  // Global listener for Copy Code buttons
  document.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('.copy-code-btn');
    if (copyBtn) {
      const targetId = copyBtn.getAttribute('data-target');
      const codeElem = document.getElementById(targetId);
      if (codeElem) {
        const rawCode = codeElem.textContent;
        navigator.clipboard.writeText(rawCode).then(() => {
          const textSpan = copyBtn.querySelector('.copy-text');
          if (textSpan) textSpan.textContent = 'Copied!';
          copyBtn.classList.add('copied');
          showToast('Code snippet copied to clipboard', '📋');
          setTimeout(() => {
            if (textSpan) textSpan.textContent = 'Copy';
            copyBtn.classList.remove('copied');
          }, 2000);
        }).catch(() => {
          showToast('Unable to copy to clipboard', '⚠️');
        });
      }
    }
  });

  // Vision Screenshot Card
  function appendScreenshotCard(data) {
    const card = document.createElement('div');
    card.className = 'message-card assistant-msg vision-msg-card';
    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const imgUrl = `${data.url}?t=${Date.now()}`;

    card.innerHTML = `
      <div class="msg-avatar-wrap">
        <div class="assistant-avatar-badge">
          <div class="avatar-glow"></div>
          <span class="avatar-initial">📸</span>
        </div>
      </div>
      <div class="msg-content-wrap">
        <div class="msg-meta-row">
          <span class="sender-name">JARVIS VISION AGENT</span>
          <span class="timestamp">${nowStr}</span>
          <span class="tag-pill tag-desktop">DESKTOP SNAPSHOT</span>
        </div>
        <div class="msg-body-text">
          <p>Active Monitor Perception: <strong>${escapeHtml(data.active_window || 'Desktop Workspace')}</strong></p>
          <div class="vision-preview-box" data-img="${imgUrl}" data-title="${escapeHtml(data.active_window || 'Screen Snapshot')}">
            <img src="${imgUrl}" alt="Monitor Capture" class="vision-preview-img" />
          </div>
        </div>
      </div>
    `;

    messagesContainer.appendChild(card);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Delegate click for Lightbox modal
  document.addEventListener('click', (e) => {
    const previewBox = e.target.closest('.vision-preview-box');
    if (previewBox) {
      const src = previewBox.getAttribute('data-img');
      const title = previewBox.getAttribute('data-title') || 'Screen Snapshot';
      if (lightboxModal && lightboxImg) {
        lightboxImg.src = src;
        if (lightboxTitle) lightboxTitle.textContent = title;
        if (lightboxDownloadBtn) lightboxDownloadBtn.href = src;
        lightboxModal.classList.add('open');
      }
    }
  });

  if (closeLightboxBtn) {
    closeLightboxBtn.addEventListener('click', () => lightboxModal.classList.remove('open'));
  }
  if (lightboxModal) {
    lightboxModal.addEventListener('click', (e) => {
      if (e.target === lightboxModal) lightboxModal.classList.remove('open');
    });
  }

  function showTyping(text) {
    if (typingText) typingText.textContent = text;
    if (typingIndicator) typingIndicator.style.display = 'flex';
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function hideTyping() {
    if (typingIndicator) typingIndicator.style.display = 'none';
  }

  // ── Speech Synthesis (Disabled to Guarantee Single Voice Output) ─────────
  function speakBrowserVoice(text) {
    // Python backend Edge-TTS plays audio directly through system speakers.
    // Browser speechSynthesis is completely silenced to eliminate dual simultaneous voice.
    if (window.speechSynthesis) {
      try { window.speechSynthesis.cancel(); } catch (e) {}
    }
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ── 60 FPS HTML5 Canvas Visualizer ────────────────────────────────────────
  let rotationAngle = 0;
  const numBars = 56;
  const barHeights = new Array(numBars).fill(0);
  const particles = [];
  const maxParticles = 40;

  for (let i = 0; i < maxParticles; i++) {
    particles.push({
      x: canvas.width / 2,
      y: canvas.height / 2,
      angle: Math.random() * Math.PI * 2,
      dist: 80 + Math.random() * 140,
      speed: 0.6 + Math.random() * 1.6,
      size: 1.2 + Math.random() * 2.2,
      alpha: 0.2 + Math.random() * 0.8,
    });
  }

  function resizeCanvas() {
    const container = canvas.parentElement;
    if (!container) return;
    const size = Math.min(container.clientWidth, container.clientHeight, 480);
    if (size > 50) {
      canvas.width = size;
      canvas.height = size;
    }
  }

  window.addEventListener('resize', resizeCanvas);
  setTimeout(resizeCanvas, 60);

  function renderVisualizer() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const pal = getStatePalette(currentState);

    // Read real-time browser microphone audio if active
    if (audioAnalyser && analyserDataArray && isListeningActive) {
      audioAnalyser.getByteFrequencyData(analyserDataArray);
      let sum = 0;
      for (let i = 0; i < analyserDataArray.length; i++) {
        sum += analyserDataArray[i];
      }
      const localNorm = Math.min((sum / analyserDataArray.length) / 75.0, 1.0);
      if (localNorm > 0.02) {
        targetEnergy = Math.max(targetEnergy, localNorm);
        updateEnergySpectrum(localNorm, localNorm * 0.006);
      }
    }

    smoothEnergy += (targetEnergy - smoothEnergy) * 0.16;

    const coreScale = 1.0 + smoothEnergy * 0.42;
    quantumCore.style.transform = `scale(${coreScale.toFixed(3)})`;

    rotationAngle += 0.008 + smoothEnergy * 0.035;

    // 1. Orbital Outer Ring
    ctx.save();
    ctx.translate(cx, cy);

    ctx.beginPath();
    ctx.arc(0, 0, 145 + smoothEnergy * 22, 0, Math.PI * 2);
    ctx.strokeStyle = pal.glow;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Rotating tech tick marks
    ctx.rotate(rotationAngle);
    const tickCount = 44;
    for (let i = 0; i < tickCount; i++) {
      const angle = (i / tickCount) * Math.PI * 2;
      const innerR = 126;
      const outerR = (i % 4 === 0) ? 138 : 132;
      ctx.beginPath();
      ctx.moveTo(Math.cos(angle) * innerR, Math.sin(angle) * innerR);
      ctx.lineTo(Math.cos(angle) * outerR, Math.sin(angle) * outerR);
      ctx.strokeStyle = (i % 4 === 0) ? pal.primary : 'rgba(255, 255, 255, 0.15)';
      ctx.lineWidth = (i % 4 === 0) ? 2 : 1;
      ctx.stroke();
    }
    ctx.restore();

    // 2. Circular Harmonic Spectrum Bars
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-rotationAngle * 0.75);

    const baseRadius = 90;
    for (let i = 0; i < numBars; i++) {
      const angle = (i / numBars) * Math.PI * 2;
      const harmonic = Math.sin(i * 0.4 + rotationAngle * 4) * Math.cos(i * 0.2);
      const targetH = Math.max(2, (Math.abs(harmonic) * 42 + Math.random() * 6) * (smoothEnergy * 1.6 + 0.1));
      barHeights[i] += (targetH - barHeights[i]) * 0.26;

      const r1 = baseRadius;
      const r2 = baseRadius + barHeights[i];

      const x1 = Math.cos(angle) * r1;
      const y1 = Math.sin(angle) * r1;
      const x2 = Math.cos(angle) * r2;
      const y2 = Math.sin(angle) * r2;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = (i % 2 === 0) ? pal.primary : pal.secondary;
      ctx.lineWidth = 2.4;
      ctx.lineCap = 'round';
      ctx.stroke();
    }
    ctx.restore();

    // 3. Particle Starfield
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.dist += p.speed * (1 + smoothEnergy * 3.2);
      if (p.dist > canvas.width * 0.46) {
        p.dist = 60 + Math.random() * 20;
        p.angle = Math.random() * Math.PI * 2;
      }

      const px = cx + Math.cos(p.angle) * p.dist;
      const py = cy + Math.sin(p.angle) * p.dist;

      ctx.beginPath();
      ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fillStyle = pal.primary;
      ctx.globalAlpha = p.alpha * (0.35 + smoothEnergy * 0.65);
      ctx.fill();
      ctx.globalAlpha = 1.0;
    }

    requestAnimationFrame(renderVisualizer);
  }

  requestAnimationFrame(renderVisualizer);

  // ── User Input & Text Form ────────────────────────────────────────────────
  inputForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = textInputField.value.trim();
    if (!text) return;

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'send_text', text }));
      textInputField.value = '';
    } else {
      appendMessage('assistant', 'Transceiver link offline: unable to send command.');
    }
  });

  // ── Unified Intelligent Voice Engine (Browser Web Speech + AudioContext + PyAudio) ──
  let speechRecognition = null;
  let isListeningActive = false;
  let userAudioStream = null;
  let audioAnalyser = null;
  let analyserDataArray = null;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function initSpeechEngine() {
    if (!SpeechRecognition) {
      console.warn('[HUD] Web Speech API not supported in this browser. Falling back to backend PyAudio.');
      return;
    }

    try {
      speechRecognition = new SpeechRecognition();
      speechRecognition.continuous = (listeningMode === 'continuous');
      speechRecognition.interimResults = true;
      speechRecognition.lang = 'en-US';

      speechRecognition.onstart = () => {
        isListeningActive = true;
        setAssistantState('HEARING');
        updateMicButtonsVisual(true);
        textInputField.placeholder = '🎙️ Listening... Speak naturally to Jarvis';
        showToast('Microphone active — Jarvis is listening', '🎙️');
      };

      speechRecognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const trans = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += trans;
          } else {
            interimTranscript += trans;
          }
        }

        if (interimTranscript && textInputField) {
          textInputField.value = `🎙️ ${interimTranscript}`;
        }

        if (finalTranscript && finalTranscript.trim()) {
          const cleanSpeech = finalTranscript.trim();
          console.log('[HUD] Speech Recognized:', cleanSpeech);
          if (textInputField) textInputField.value = cleanSpeech;

          // Wake-word checking if in wakeword mode
          if (listeningMode === 'wakeword') {
            const lower = cleanSpeech.toLowerCase();
            if (!lower.includes('jarvis') && !lower.includes('mini')) {
              console.log('[HUD] Ignored speech in wake-word mode (no "Jarvis" keyword detected).');
              if (textInputField) textInputField.value = '';
              return;
            }
          }

          // Transmit command to Jarvis
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'send_text', text: cleanSpeech }));
            playActivationChime();
            setTimeout(() => {
              if (textInputField) textInputField.value = '';
            }, 600);
          }
        }
      };

      speechRecognition.onerror = (event) => {
        console.warn('[HUD] Speech recognition event error:', event.error);
        if (event.error === 'not-allowed') {
          showToast('Microphone permission blocked. Please click the lock/mic icon in browser address bar to allow.', '⚠️');
          isListeningActive = false;
          updateMicButtonsVisual(false);
        } else if (event.error === 'no-speech') {
          // Normal timeout on silence
        }
      };

      speechRecognition.onend = () => {
        // In continuous mode, restart if still active
        if (isListeningActive && listeningMode === 'continuous') {
          try {
            speechRecognition.start();
          } catch (e) {}
        } else if (!isPttHeld) {
          isListeningActive = false;
          updateMicButtonsVisual(false);
          if (textInputField && textInputField.placeholder.includes('Listening')) {
            textInputField.placeholder = 'Speak naturally, hold Spacebar, or type a command...';
          }
          if (currentState === 'HEARING') {
            setAssistantState('LISTENING');
          }
        }
      };
    } catch (err) {
      console.error('[HUD] Failed to initialize SpeechRecognition:', err);
    }
  }

  // Connect browser audio analyser for live audio reactive feedback
  async function startBrowserAudioMeter() {
    try {
      if (userAudioStream) return;
      userAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      const actx = getAudioContext();
      if (actx) {
        const source = actx.createMediaStreamSource(userAudioStream);
        audioAnalyser = actx.createAnalyser();
        audioAnalyser.fftSize = 64;
        source.connect(audioAnalyser);
        analyserDataArray = new Uint8Array(audioAnalyser.frequencyBinCount);
      }
    } catch (e) {
      console.warn('[HUD] Browser microphone getUserMedia warning:', e);
    }
  }

  function updateMicButtonsVisual(isActive) {
    if (isActive) {
      if (deckMicBtn) {
        deckMicBtn.className = 'deck-mic-button active';
        deckMicBtn.style.borderColor = 'var(--primary)';
        deckMicBtn.style.boxShadow = 'var(--glow-primary)';
      }
      if (micToggleBtn) micToggleBtn.className = 'action-icon-btn active';
      if (micBtnLabel) micBtnLabel.textContent = 'Mic Live';
    } else {
      if (deckMicBtn) {
        deckMicBtn.className = 'deck-mic-button muted';
        deckMicBtn.style.borderColor = '';
        deckMicBtn.style.boxShadow = '';
      }
      if (micToggleBtn) micToggleBtn.className = 'action-icon-btn muted';
      if (micBtnLabel) micBtnLabel.textContent = 'Muted';
    }
  }

  // Toggle Voice Input (Triggered by Deck Mic or Header Mic)
  function toggleVoiceInput() {
    // Also notify backend to toggle PyAudio mic state
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'toggle_mic' }));
    }

    if (isListeningActive) {
      // Stop browser listening
      isListeningActive = false;
      if (speechRecognition) {
        try { speechRecognition.stop(); } catch (e) {}
      }
      updateMicButtonsVisual(false);
      setAssistantState('MUTED');
      showToast('Microphone deactivated', '🔇');
    } else {
      // Start browser listening
      isListeningActive = true;
      startBrowserAudioMeter();
      if (speechRecognition) {
        try {
          speechRecognition.continuous = (listeningMode === 'continuous');
          speechRecognition.start();
        } catch (e) {
          try { speechRecognition.stop(); speechRecognition.start(); } catch (e2) {}
        }
      }
      updateMicButtonsVisual(true);
      setAssistantState('LISTENING');
    }
  }

  if (micToggleBtn) micToggleBtn.addEventListener('click', toggleVoiceInput);
  if (deckMicBtn) deckMicBtn.addEventListener('click', toggleVoiceInput);

  initSpeechEngine();

  // Voice Output Toggle Button
  if (voiceOutputToggleBtn) {
    voiceOutputToggleBtn.addEventListener('click', () => {
      voiceOutputEnabled = !voiceOutputEnabled;
      if (voiceOutputEnabled) {
        voiceOutputToggleBtn.className = 'action-icon-btn active';
        if (voiceBtnLabel) voiceBtnLabel.textContent = 'Audio';
        showToast('Voice audio feedback activated', '🔊');
      } else {
        voiceOutputToggleBtn.className = 'action-icon-btn muted';
        if (voiceBtnLabel) voiceBtnLabel.textContent = 'Muted';
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        showToast('Voice audio feedback muted', '🔇');
      }
    });
  }

  // Listening Mode Switcher
  function setListeningMode(mode) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'set_listening_mode', mode }));
    }
    showToast(`Listening Mode set to ${mode.toUpperCase()}`, '🎙️');
  }

  if (modeContinuousBtn) modeContinuousBtn.addEventListener('click', () => setListeningMode('continuous'));
  if (modeWakewordBtn) modeWakewordBtn.addEventListener('click', () => setListeningMode('wakeword'));
  if (modePttBtn) modePttBtn.addEventListener('click', () => setListeningMode('ptt'));

  // Push-To-Talk (PTT) Keyboard Spacebar Listener
  window.addEventListener('keydown', (e) => {
    if (listeningMode !== 'ptt') return;
    if (e.code === 'Space' && document.activeElement !== textInputField) {
      e.preventDefault();
      if (!isPttHeld) {
        isPttHeld = true;
        if (pttTriggerBtn) pttTriggerBtn.classList.add('active');
        playActivationChime();
        if (speechRecognition) {
          try {
            speechRecognition.continuous = false;
            speechRecognition.start();
          } catch (err) {}
        }
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: 'set_ptt', active: true }));
        }
      }
    }
  });

  window.addEventListener('keyup', (e) => {
    if (listeningMode !== 'ptt') return;
    if (e.code === 'Space' && document.activeElement !== textInputField) {
      e.preventDefault();
      if (isPttHeld) {
        isPttHeld = false;
        if (pttTriggerBtn) pttTriggerBtn.classList.remove('active');
        if (speechRecognition) {
          try { speechRecognition.stop(); } catch (err) {}
        }
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: 'set_ptt', active: false }));
        }
      }
    }
  });

  // Dedicated PTT Button Mouse/Touch Events
  if (pttTriggerBtn) {
    const handlePttStart = (e) => {
      e.preventDefault();
      isPttHeld = true;
      pttTriggerBtn.classList.add('active');
      playActivationChime();
      if (speechRecognition) {
        try {
          speechRecognition.continuous = false;
          speechRecognition.start();
        } catch (err) {}
      }
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'set_ptt', active: true }));
      }
    };
    const handlePttEnd = (e) => {
      e.preventDefault();
      if (isPttHeld) {
        isPttHeld = false;
        pttTriggerBtn.classList.remove('active');
        if (speechRecognition) {
          try { speechRecognition.stop(); } catch (err) {}
        }
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: 'set_ptt', active: false }));
        }
      }
    };
    pttTriggerBtn.addEventListener('mousedown', handlePttStart);
    pttTriggerBtn.addEventListener('mouseup', handlePttEnd);
    pttTriggerBtn.addEventListener('touchstart', handlePttStart);
    pttTriggerBtn.addEventListener('touchend', handlePttEnd);
  }

  // Instant Barge-In Stop Speech Button
  if (haltSpeechBtn) {
    haltSpeechBtn.addEventListener('click', () => {
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      playCancelChime();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'stop_speech' }));
      }
      setAssistantState('LISTENING');
    });
  }

  // Layout View Switcher
  function setViewMode(mode) {
    [viewSplitBtn, viewChatBtn, viewHudBtn].forEach(b => {
      if (b) b.classList.remove('active');
    });
    if (hudWorkspace) {
      hudWorkspace.className = `hud-workspace view-mode-${mode}`;
    }
    if (mode === 'split' && viewSplitBtn) viewSplitBtn.classList.add('active');
    if (mode === 'chat' && viewChatBtn) viewChatBtn.classList.add('active');
    if (mode === 'hud' && viewHudBtn) viewHudBtn.classList.add('active');
    setTimeout(resizeCanvas, 150);
  }

  if (viewSplitBtn) viewSplitBtn.addEventListener('click', () => setViewMode('split'));
  if (viewChatBtn) viewChatBtn.addEventListener('click', () => setViewMode('chat'));
  if (viewHudBtn) viewHudBtn.addEventListener('click', () => setViewMode('hud'));

  // Quick Action Chips
  document.querySelectorAll('.prompt-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'send_text', text: prompt }));
      }
    });
  });

  // Clear Chat Button
  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      messagesContainer.innerHTML = '';
      showToast('Conversation stream cleared', '🗑️');
    });
  }

  // ── Unified Text Input Submission ──────────────────────────────────────────
  function submitUserText() {
    if (!textInputField) return;
    const text = textInputField.value.trim();
    if (!text) return;

    console.log('[HUD] Transmitting user text:', text);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'send_text', text: text }));
      textInputField.value = '';
      playActivationChime();
      setAssistantState('THINKING');
    } else {
      showToast('Connecting to Jarvis brain...', '⚡');
    }
  }

  if (inputForm) {
    inputForm.addEventListener('submit', (e) => {
      e.preventDefault();
      submitUserText();
    });
  }

  if (textInputField) {
    textInputField.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitUserText();
      }
    });
  }

  const sendBtn = document.getElementById('sendBtn');
  if (sendBtn) {
    sendBtn.addEventListener('click', (e) => {
      e.preventDefault();
      submitUserText();
    });
  }

  // ── Settings & Customization Modal ────────────────────────────────────────
  function openSettings() {
    if (settingsModalBackdrop) settingsModalBackdrop.classList.add('open');
  }

  function closeSettings() {
    if (settingsModalBackdrop) settingsModalBackdrop.classList.remove('open');
  }

  if (openSettingsBtn) openSettingsBtn.addEventListener('click', openSettings);
  if (closeSettingsBtn) closeSettingsBtn.addEventListener('click', closeSettings);
  if (saveSettingsBtn) saveSettingsBtn.addEventListener('click', closeSettings);
  if (settingsModalBackdrop) {
    settingsModalBackdrop.addEventListener('click', (e) => {
      if (e.target === settingsModalBackdrop) closeSettings();
    });
  }

  // Theme Picker
  themeCards.forEach((card) => {
    card.addEventListener('click', () => {
      const selected = card.getAttribute('data-theme');
      document.body.className = selected;
      localStorage.setItem('jarvis_hud_theme', selected);
      updateActiveThemeCard(selected);
      setAssistantState(currentState);
      showToast(`HUD Theme updated to ${card.querySelector('.theme-name').textContent}`, '🎨');
    });
  });

  // Voice Persona Selector
  if (voicePersonaSelect) {
    voicePersonaSelect.addEventListener('change', (e) => {
      selectedVoiceGender = e.target.value;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'set_voice', gender: selectedVoiceGender }));
      }
      showToast(`Voice persona switched to ${selectedVoiceGender.toUpperCase()}`, '🗣️');
    });
  }

  // Speech Rate Range Slider
  if (speechRateRange) {
    speechRateRange.addEventListener('input', (e) => {
      speechRateModifier = parseInt(e.target.value, 10);
      const mult = (1 + speechRateModifier / 100).toFixed(2);
      if (speechRateVal) speechRateVal.textContent = `${mult}x`;
    });
    speechRateRange.addEventListener('change', (e) => {
      speechRateModifier = parseInt(e.target.value, 10);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'set_speech_rate', rate: speechRateModifier }));
      }
    });
  }

  // SFX Toggle & Test Chime
  if (sfxToggleBtn) {
    sfxToggleBtn.addEventListener('click', () => {
      sfxEnabled = !sfxEnabled;
      if (sfxEnabled) {
        sfxToggleBtn.classList.add('active');
        playActivationChime();
        showToast('Acoustic SFX chimes enabled', '🔔');
      } else {
        sfxToggleBtn.classList.remove('active');
        showToast('Acoustic SFX chimes disabled', '🔕');
      }
    });
  }

  if (testChimeBtn) {
    testChimeBtn.addEventListener('click', () => {
      playActivationChime();
      setTimeout(playCompletionChime, 250);
    });
  }

  // VAD Threshold Sensitivity Slider
  if (vadThresholdRange) {
    vadThresholdRange.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      if (vadThresholdVal) vadThresholdVal.textContent = val.toFixed(4);
      updateThresholdMarker(val);
    });
    vadThresholdRange.addEventListener('change', (e) => {
      const val = parseFloat(e.target.value);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'set_threshold', value: val }));
      }
      showToast(`Perception sensitivity threshold adjusted`, '⚡');
    });
  }

  // ── Memory & Subsystems Drawer ────────────────────────────────────────────
  function openDrawer() {
    if (memoryDrawer && drawerScrim) {
      memoryDrawer.classList.add('open');
      drawerScrim.classList.add('open');
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'get_memory' }));
      }
    }
  }

  function closeDrawer() {
    if (memoryDrawer && drawerScrim) {
      memoryDrawer.classList.remove('open');
      drawerScrim.classList.remove('open');
    }
  }

  if (openMemoryBtn) openMemoryBtn.addEventListener('click', openDrawer);
  if (closeMemoryBtn) closeMemoryBtn.addEventListener('click', closeDrawer);
  if (drawerScrim) drawerScrim.addEventListener('click', closeDrawer);

  if (tabMemoriesBtn && tabToolsBtn) {
    tabMemoriesBtn.addEventListener('click', () => {
      tabMemoriesBtn.classList.add('active');
      tabToolsBtn.classList.remove('active');
      paneMemories.style.display = 'flex';
      paneTools.style.display = 'none';
    });

    tabToolsBtn.addEventListener('click', () => {
      tabToolsBtn.classList.add('active');
      tabMemoriesBtn.classList.remove('active');
      paneMemories.style.display = 'none';
      paneTools.style.display = 'grid';
    });
  }

  function renderMemoryData(memories, tools) {
    cachedMemories = memories;
    renderMemoryList(memories);

    if (toolsGrid) {
      toolsGrid.innerHTML = tools.map(tool => `
        <div class="tool-tile">
          <div class="tool-tile-header">
            <span class="tool-tile-name">${escapeHtml(tool.name)}</span>
            <span class="tool-badge-status">${escapeHtml(tool.status)}</span>
          </div>
          <div class="tool-tile-desc">${escapeHtml(tool.desc)}</div>
        </div>
      `).join('');
    }
  }

  function renderMemoryList(memories) {
    if (!memoryList) return;
    if (!memories || memories.length === 0) {
      memoryList.innerHTML = '<div class="memory-card-item" style="text-align: center; color: var(--text-muted);">No episodic memories archived yet.</div>';
      return;
    }

    memoryList.innerHTML = memories.map(m => `
      <div class="memory-card-item">
        <div class="memory-card-meta">
          <span class="memory-role-badge ${m.role === 'user' ? 'user' : 'assistant'}">${m.role.toUpperCase()}</span>
          <span>${m.time || ''}</span>
        </div>
        <div>${escapeHtml(m.content)}</div>
      </div>
    `).join('');
  }

  if (memorySearchInput) {
    memorySearchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) {
        renderMemoryList(cachedMemories);
      } else {
        const filtered = cachedMemories.filter(m => (m.content || '').toLowerCase().includes(q));
        renderMemoryList(filtered);
      }
    });
  }

  // ── Auxiliary Browser Mic Button ──────────────────────────────────────────
  if (browserMicBtn) {
    browserMicBtn.addEventListener('click', toggleVoiceInput);
  }

  // ── Global Keyboard Shortcuts ────────────────────────────────────────────
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeSettings();
      closeDrawer();
      if (lightboxModal) lightboxModal.classList.remove('open');
    }
  });

  // Connect WebSocket on Load
  connectWebSocket();
})();
