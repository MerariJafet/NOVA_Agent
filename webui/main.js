// main.js - chat & UI logic adapted to the new index.html IDs
const state = { sessionId: 'webui_' + Date.now(), streaming: false, voiceActive: false };
let voiceRecognition = null;

const els = {
    messagesContainer: () => document.getElementById('messages-container'),
    messageInput: () => document.getElementById('message-input'),
    sendBtn: () => document.getElementById('send-btn'),
    micBtn: () => document.getElementById('mic-btn'),
    voicePushBtn: () => document.getElementById('voice-push-btn'),
    aiAdviceBtn: () => document.getElementById('ai-advice-btn'),
    engineStatus: () => document.getElementById('engine-status'),
    autoOptimizeBtn: () => document.getElementById('auto-optimize-btn')
};

function setupEventListeners() {
    const send = els.sendBtn();
    const input = els.messageInput();
    if (send) send.addEventListener('click', () => sendMessage());
    if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });

    const autoBtn = els.autoOptimizeBtn();
    if (autoBtn) autoBtn.addEventListener('click', triggerAutoOptimize);

    const voicePush = els.voicePushBtn();
    if (voicePush) voicePush.addEventListener('click', toggleVoiceConversation);

    const aiAdvice = els.aiAdviceBtn();
    if (aiAdvice) aiAdvice.addEventListener('click', triggerAIAdvice);
}

async function sendMessage(textOverride = null, opts = {}) {
    const input = els.messageInput();
    const send = els.sendBtn();
    const container = els.messagesContainer();
    if (!input || !send || !container) return;
    const text = (textOverride !== null ? textOverride : input.value).trim();
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
        if (data.status === 'clarify') {
            contentEl.textContent = data.message || 'Necesito un poco más de contexto.';
            maybeSpeak(contentEl.textContent, opts);
            return;
        }
        const reply = data.response || '[sin respuesta]';
        contentEl.textContent = reply;
        if (isFallback(reply)) {
            const warn = addMessage('assistant', '⚠️ Motor no respondió. Verifica que Ollama esté corriendo en http://localhost:11434 o reinicia el backend.');
            warn.classList.add('warning');
        }
        maybeSpeak(reply, opts);
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
        if (window.loadCharts) window.loadCharts();
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
            document.getElementById('image-input').value = '';
            document.getElementById('image-instruction').value = '';
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
    const instruction = document.getElementById('image-instruction').value.trim() || 'Describe esta imagen';
    formData.append('message', instruction);
    formData.append('session_id', state.sessionId);

    addMessage('user', `📷 Imagen subida: ${file.name} - Instrucción: ${instruction}`);
    const assistantEl = addMessage('assistant', '...');
    const contentEl = assistantEl.querySelector('.message-content');

    try {
        console.log('Uploading image to http://localhost:8000/api/upload');
        const res = await fetch('http://localhost:8000/api/upload', { method: 'POST', body: formData });
        console.log('Upload response status:', res.status);
        document.getElementById('image-modal').style.display = 'none'; // Cerrar modal después de enviar
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        console.log('Upload response data:', data);
        contentEl.textContent = data.response || '[sin respuesta]';
        maybeSpeak(contentEl.textContent);
    } catch (err) {
        console.error('sendImage error', err);
        contentEl.textContent = '❌ Error al subir imagen';
    } finally {
        scrollToBottom();
        document.getElementById('image-modal').style.display = 'none';
        document.getElementById('image-input').value = '';
        document.getElementById('image-instruction').value = '';
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
        const mic = els.micBtn();
        if (mic) mic.textContent = '🎤 Grabando...';
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('message-input').value = transcript;
        sendMessage(transcript, { speakResponse: true }); // Auto-send after voice input
    };

    recognition.onerror = (event) => {
        console.error('Voice recognition error:', event.error);
        const mic = els.micBtn();
        if (mic) mic.textContent = '🎤';
    };

    recognition.onend = () => {
        const mic = els.micBtn();
        if (mic) mic.textContent = '🎤';
    };

    recognition.start();
}

document.addEventListener('DOMContentLoaded', () => { setupEventListeners(); setupMultimediaListeners(); refreshMetrics(); setInterval(refreshMetrics, 1000); });
document.addEventListener('DOMContentLoaded', () => { checkEngines(); setInterval(checkEngines, 8000); });

// Ensure send button & enter key are wired (explicitly per Sofía's request)
function ensureSendWiring(){
    const send = document.getElementById('send-btn');
    const input = document.getElementById('message-input');
    if (send) send.onclick = () => sendMessage();
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

async function triggerAutoOptimize(){
    const btn = els.autoOptimizeBtn();
    if (!btn) return;
    btn.disabled = true;
    btn.textContent = '⏳ OPTIMIZANDO...';
    try{
        const res = await fetch('http://localhost:8000/api/auto-tuning/optimize', { method:'POST' });
        if(!res.ok) throw new Error('HTTP '+res.status);
        const data = await res.json();
        addMessage('assistant', `Auto-Optimize ejecutado: ${data.status || 'ok'}`);
    }catch(err){
        console.error('autoOptimize', err);
        addMessage('assistant', '❌ Error al auto-optimizar');
    }finally{
        btn.disabled = false;
        btn.textContent = '🚀 AUTO-OPTIMIZE';
    }
}

async function triggerAIAdvice(){
    const btn = els.aiAdviceBtn();
    if (!btn) return;
    btn.disabled = true;
    btn.textContent = '🤖 CONSULTANDO...';
    try{
        const res = await fetch('http://localhost:8000/api/agents/query', { 
            method:'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: "Dame un consejo útil sobre productividad y eficiencia en el trabajo", session_id: state.sessionId })
        });
        if(!res.ok) throw new Error('HTTP '+res.status);
        const data = await res.json();
        const advice = data.agent_response || 'No se pudo obtener consejo';
        addMessage('assistant', `🤖 Consejo IA: ${advice}`);
    }catch(err){
        console.error('aiAdvice', err);
        addMessage('assistant', '❌ Error al obtener consejo IA');
    }finally{
        btn.disabled = false;
        btn.textContent = '🤖 Consejo IA';
    }
}

function ensureSpeechSupport(){
    const speechOk = 'speechSynthesis' in window;
    const sttOk = ('webkitSpeechRecognition' in window) || ('SpeechRecognition' in window);
    return speechOk && sttOk;
}

function toggleVoiceConversation(){
    if(!ensureSpeechSupport()){
        alert('Tu navegador no soporta conversación por voz.');
        return;
    }
    state.voiceActive = !state.voiceActive;
    const btn = els.voicePushBtn();
    if(btn) btn.textContent = state.voiceActive ? '🛑 Detener Voz' : '🎙️ Push Voz';
    if(state.voiceActive){
        startVoiceLoop();
    }else{
        stopVoiceLoop();
    }
}

function startVoiceLoop(){
    if(!ensureSpeechSupport()) return;
    if(voiceRecognition){
        try{ voiceRecognition.stop(); }catch(e){}
    }
    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    voiceRecognition = new Rec();
    voiceRecognition.lang = 'es-ES';
    voiceRecognition.continuous = true;
    voiceRecognition.interimResults = false;
    voiceRecognition.onstart = ()=>{
        const btn = els.voicePushBtn();
        if(btn) btn.classList.add('listening');
    };
    voiceRecognition.onerror = (e)=>{
        console.error('voice loop error', e);
        toggleVoiceConversation();
    };
    voiceRecognition.onend = ()=>{
        const btn = els.voicePushBtn();
        if(btn) btn.classList.remove('listening');
        if(state.voiceActive){
            // Restart to keep hands-free flow
            startVoiceLoop();
        }
    };
    voiceRecognition.onresult = (event)=>{
        const transcript = event.results[event.results.length-1][0].transcript;
        if(transcript){
            try{ voiceRecognition.stop(); }catch(e){}
            addMessage('user', `🎙️ ${transcript}`);
            sendMessage(transcript, { speakResponse:true });
        }
    };
    voiceRecognition.start();
}

function isFallback(text=''){
    return text.includes('[NOVA fallback');
}

function stopVoiceLoop(){
    if(voiceRecognition){
        try{ voiceRecognition.stop(); }catch(e){}
        voiceRecognition = null;
    }
    const btn = els.voicePushBtn();
    if(btn) btn.classList.remove('listening');
}

function maybeSpeak(text, opts={}){
    const shouldSpeak = opts.speakResponse || state.voiceActive;
    if(!shouldSpeak) return;
    if(!('speechSynthesis' in window)) return;
    try{
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = 'es-ES';
        speechSynthesis.cancel();
        speechSynthesis.speak(utter);
    }catch(e){
        console.warn('speech synthesis failed', e);
    }
}

async function checkEngines(){
    const badge = els.engineStatus();
    if(!badge) return;
    try{
        const res = await fetch('http://localhost:8000/api/engines/health');
        if(!res.ok) throw new Error('HTTP '+res.status);
        const data = await res.json();
        const ollama = data.engines?.ollama || 'unknown';
        if(ollama === 'ok'){
            badge.textContent = 'Motores: OK';
            badge.classList.add('online');
            badge.classList.remove('offline');
        }else{
            badge.textContent = `Motores: ${ollama}`;
            badge.classList.add('offline');
            badge.classList.remove('online');
        }
    }catch(err){
        badge.textContent = 'Motores: offline';
        badge.classList.add('offline');
        badge.classList.remove('online');
    }
}
