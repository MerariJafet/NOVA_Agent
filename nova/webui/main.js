// main.js - chat & UI logic adapted to the new index.html IDs
const state = { sessionId: 'webui_' + Date.now(), streaming: false };

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
        contentEl.textContent = data.response || '[sin respuesta]';
    } catch (err) {
        console.error('sendMessage error', err);
        contentEl.textContent = '❌ Error al enviar mensaje';
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

function setupMultimediaListeners(){
    const imgBtn = document.getElementById('image-btn');
    if (imgBtn) imgBtn.addEventListener('click', () => {
        document.getElementById('image-input').click();
    });

    const imageInput = document.getElementById('image-input');
    if (imageInput) imageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById('image-preview').src = e.target.result;
                document.getElementById('image-modal').style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });

    const closeModal = document.querySelector('.close');
    if (closeModal) closeModal.addEventListener('click', () => {
        document.getElementById('image-modal').style.display = 'none';
    });

    const sendImageBtn = document.getElementById('send-image-btn');
    if (sendImageBtn) sendImageBtn.addEventListener('click', async () => {
        const file = document.getElementById('image-input').files[0];
        if (file) {
            await sendImage(file);
            document.getElementById('image-modal').style.display = 'none';
        }
    });

    const micBtn = document.getElementById('mic-btn');
    if (micBtn) micBtn.addEventListener('click', startVoiceInput);

    const ttsBtn = document.getElementById('tts-btn');
    if (ttsBtn) ttsBtn.addEventListener('click', ()=>{ /* placeholder */ });
}

async function sendImage(file) {
    const formData = new FormData();
    formData.append('file', file);

    addMessage('user', `📷 Imagen subida: ${file.name}`);
    const assistantEl = addMessage('assistant', '...');
    const contentEl = assistantEl.querySelector('.message-content');

    try {
        console.log('Uploading image to http://localhost:8000/api/upload');
        const res = await fetch('http://localhost:8000/api/upload', { method: 'POST', body: formData });
        console.log('Upload response status:', res.status);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        console.log('Upload response data:', data);
        contentEl.textContent = data.response || '[sin respuesta]';
    } catch (err) {
        console.error('sendImage error', err);
        contentEl.textContent = '❌ Error al subir imagen';
    } finally {
        scrollToBottom();
    }
}

function startVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Tu navegador no soporta reconocimiento de voz.');
        return;
    }

    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'es-ES'; // Spanish
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        document.getElementById('mic-btn').textContent = '🎤 Grabando...';
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('message-input').value = transcript;
        sendMessage(); // Auto-send after voice input
    };

    recognition.onerror = (event) => {
        console.error('Voice recognition error:', event.error);
        document.getElementById('mic-btn').textContent = '🎤';
    };

    recognition.onend = () => {
        document.getElementById('mic-btn').textContent = '🎤';
    };

    recognition.start();
}

document.addEventListener('DOMContentLoaded', () => { setupEventListeners(); setupMultimediaListeners(); refreshMetrics(); setInterval(refreshMetrics, 10000); });

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

// === BOTÓN CÁMARA ===
function handleImageSelect(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('image-preview').src = e.target.result;
        document.getElementById('image-modal').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

document.getElementById('camera-btn').addEventListener('click', () => {
  document.getElementById('file-input').click();
});

document.getElementById('file-input').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) handleImageSelect(file);
});

// === BOTÓN MICRÓFONO ===
let recognition = null;
let isRecording = false;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'es-ES';

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map(result => result[0].transcript)
      .join('');
    document.getElementById('message-input').value = transcript;
  };

  recognition.onend = () => {
    document.getElementById('mic-btn').classList.remove('recording');
    isRecording = false;
  };

  document.getElementById('mic-btn').addEventListener('click', () => {
    if (isRecording) {
      recognition.stop();
    } else {
      recognition.start();
      document.getElementById('mic-btn').classList.add('recording');
      isRecording = true;
    }
  });
} else {
  document.getElementById('mic-btn').style.opacity = '0.5';
  document.getElementById('mic-btn').title = 'Micrófono no soportado en este navegador';
}

// === MODAL DE IMAGEN ===
document.querySelector('.close').addEventListener('click', () => {
  document.getElementById('image-modal').style.display = 'none';
});

document.getElementById('send-image-btn').addEventListener('click', async () => {
  const file = document.getElementById('file-input').files[0];
  if (file) {
    await sendImage(file);
    document.getElementById('image-modal').style.display = 'none';
  }
});
