// main.js - chat & UI logic adapted to the new index.html IDs
const state = { sessionId: 'webui_' + Date.now(), streaming: false, voiceMode: 'push', alwaysListening: false };
let currentSessionId = state.sessionId;

const els = {
    messagesContainer: () => document.getElementById('messages-container'),
    messageInput: () => document.getElementById('message-input'),
    sendBtn: () => document.getElementById('send-btn')
};

function setupEventListeners() {
    const send = els.sendBtn();
    const input = els.messageInput();
    if (send) send.addEventListener('click', sendMessage);
    if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    setupCameraFlow();
    setupMicFlow();
}

async function sendMessage() {
    const input = els.messageInput();
    const send = els.sendBtn();
    const container = els.messagesContainer();
    if (!input || !send || !container) return;
    const text = input.value.trim();
    if (!text || state.streaming) return;

    addMessage('user', text);
    input.value = '';
    send.disabled = true; state.streaming = true;

    const assistantEl = addMessage('assistant', '...');
    const contentEl = assistantEl.querySelector('.message-content');

    try {
        console.log('Sending message to http://localhost:8000/api/chat:', { message: text, session_id: state.sessionId });
        const res = await fetch('http://localhost:8000/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, session_id: state.sessionId }) });
        console.log('Chat response status:', res.status);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        console.log('Chat response data:', data);
        if (contentEl) contentEl.textContent = data.response || '[sin respuesta]';
    } catch (err) {
        console.error('sendMessage error', err);
        if (contentEl) contentEl.textContent = '❌ Error al enviar mensaje';
    } finally {
        send.disabled = false; state.streaming = false; scrollToBottom();
    }
}

function addMessage(who, text) {
    const container = els.messagesContainer();
    if (!container) return document.createElement('div');
    const m = document.createElement('div'); m.className = `message ${who}`;
    const c = document.createElement('div'); c.className = 'message-content'; c.textContent = text;
    m.appendChild(c);
    if (who === 'assistant' && text) addCopyButton(m, text);
    container.appendChild(m); return m;
}

function addCopyButton(messageDiv, text) {
    const a = document.createElement('div'); a.className='message-actions';
    const b = document.createElement('button'); b.className='copy-btn'; b.textContent='📋 Copiar';
    b.onclick = () => navigator.clipboard.writeText(text).then(()=>{ b.textContent='✅ Copiado!'; setTimeout(()=>b.textContent='📋 Copiar',2000); }).catch(()=>{});
    a.appendChild(b); messageDiv.appendChild(a);
}

function scrollToBottom(){ const c = els.messagesContainer(); if (c) c.scrollTop = c.scrollHeight; }

async function refreshMetrics() {
    try {
        // charts.js handles its own refresh; we just call it by re-running init
        if (window.NOVACharts && typeof window.NOVACharts.initFromData === 'function') window.NOVACharts.initFromData();
        // also call charts loader
        if (window.__chartsInit) window.__chartsInit();
    } catch(e){ console.error('refreshMetrics', e); }
}

document.addEventListener('DOMContentLoaded', () => { setupEventListeners(); refreshMetrics(); setInterval(refreshMetrics, 10000); });

// Ensure send button & enter key are wired (explicitly per Sofía's request)
function ensureSendWiring(){
    const send = document.getElementById('send-btn');
    const input = document.getElementById('message-input');
    if (send) send.onclick = sendMessage;
    if (input) input.addEventListener('keyup', (e)=>{ if (e.key === 'Enter') sendMessage(); });
}

// wire up explicit handlers after DOM ready
document.addEventListener('DOMContentLoaded', ()=>{ ensureSendWiring(); });

// Ensure charts and avatar initialize after full load
window.onload = () => {
    try {
        if (window.loadCharts) window.loadCharts();
    } catch(e){ console.error('loadCharts error', e); }
    try {
        if (window.initAvatar) window.initAvatar();
    } catch(e){ console.error('initAvatar error', e); }
};

// === CÁMARA → PREVIEW Y ENVÍO ===
function setupCameraFlow(){
  const camBtn = document.getElementById('camera-btn');
  const fileInput = document.getElementById('file-input');
  const previewModal = document.getElementById('image-preview-modal');
  const previewImg = document.getElementById('preview-img');
  const sendImageBtn = document.getElementById('send-image-btn');
  const cancelImageBtn = document.getElementById('cancel-image-btn');
  if (!camBtn || !fileInput || !previewModal || !previewImg || !sendImageBtn || !cancelImageBtn) return;

  let selectedFile = null;
  camBtn.onclick = () => fileInput.click();

  fileInput.onchange = (e) => {
    selectedFile = e.target.files[0];
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        previewImg.src = ev.target.result;
        previewModal.classList.remove('hidden');
      };
      reader.readAsDataURL(selectedFile);
    }
  };

  sendImageBtn.onclick = async () => {
    if (!selectedFile) return;
    
    const instruction = document.getElementById('image-instruction').value.trim() || 'Describe esta imagen';
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('session_id', currentSessionId || 'default');
    formData.append('message', instruction);

    addMessage('user', `[Imagen enviada] Instrucción: "${instruction}"`);
    previewModal.classList.add('hidden');

    try {
      const response = await fetch('http://localhost:8000/api/upload', { method: 'POST', body: formData });
      const data = await response.json();
      addMessage('assistant', data.analysis || data.response || 'Imagen enviada');
    } catch (e) {
      console.error('upload error', e);
      addMessage('assistant', '❌ Error al subir imagen');
    }

    selectedFile = null;
    fileInput.value = '';
    document.getElementById('image-instruction').value = '';
  };

  cancelImageBtn.onclick = () => {
    previewModal.classList.add('hidden');
    selectedFile = null;
    fileInput.value = '';
  };
}

// === MICRÓFONO: PUSH-TO-TALK Y MODO SIEMPRE ACTIVO ===
let recognition = null;
let isRecording = false;
let autoRestart = false;

function setupMicFlow(){
  const micBtn = document.getElementById('mic-btn');
  const toggleBtn = document.getElementById('voice-toggle-btn');
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition || !micBtn || !toggleBtn) return;

  recognition = new SpeechRecognition();
  recognition.lang = 'es-ES';
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results).map(r => r[0].transcript).join('');
    document.getElementById('message-input').value = transcript;
  };

  recognition.onend = () => {
    micBtn.classList.remove('recording');
    isRecording = false;
    const text = document.getElementById('message-input').value.trim();
    if (text) document.getElementById('send-btn').click();
    if (autoRestart) {
      setTimeout(() => { tryStartListening(); }, 300);
    }
  };

  function tryStartListening(){
    if (!recognition) return;
    try {
      recognition.start();
      micBtn.classList.add('recording');
      isRecording = true;
    } catch(e){
      console.error('start listening failed', e);
    }
  }

  function stopListening(){
    autoRestart = false;
    if (recognition && isRecording) recognition.stop();
  }

  micBtn.onclick = () => {
    if (state.voiceMode === 'push') {
      if (isRecording) {
        stopListening();
      } else {
        recognition.continuous = false;
        autoRestart = false;
        tryStartListening();
      }
    } else {
      // en modo siempre activo, el botón mic detiene/arranca la escucha continua
      if (isRecording) {
        stopListening();
      } else {
        recognition.continuous = true;
        autoRestart = true;
        tryStartListening();
      }
    }
  };

  toggleBtn.onclick = () => {
    if (state.voiceMode === 'push') {
      state.voiceMode = 'always';
      state.alwaysListening = true;
      toggleBtn.textContent = 'Voz: Siempre';
      recognition.continuous = true;
      autoRestart = true;
      tryStartListening();
    } else {
      state.voiceMode = 'push';
      state.alwaysListening = false;
      toggleBtn.textContent = 'Voz: Push';
      stopListening();
    }
  };
}
