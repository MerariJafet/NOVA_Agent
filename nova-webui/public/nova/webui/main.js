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
    const imgBtn = document.getElementById('image-btn'); if (imgBtn) imgBtn.addEventListener('click', ()=>{ document.getElementById('message-input').focus(); });
    const micBtn = document.getElementById('mic-btn'); if (micBtn) micBtn.addEventListener('click', ()=>{ /* placeholder */ });
    const ttsBtn = document.getElementById('tts-btn'); if (ttsBtn) ttsBtn.addEventListener('click', ()=>{ /* placeholder */ });
}

document.addEventListener('DOMContentLoaded', () => { setupEventListeners(); setupMultimediaListeners(); refreshMetrics(); setInterval(refreshMetrics, 10000); });

// Ensure send button & enter key are wired (explicitly per Sofía's request)
function ensureSendWiring(){
    const send = document.getElementById('send-btn');
    const input = document.getElementById('message-input');
    if (send) send.onclick = sendMessage;
    if (input) input.addEventListener('keyup', (e)=>{ if (e.key === 'Enter') sendMessage(); });
}

// Add simple addMessage function that creates visible bubbles
function addMessage(role, text){
    const container = document.getElementById('messages-container');
    if(!container) return;
    const msg = document.createElement('div');
    msg.className = role === 'user' ? 'message-user' : 'message-ai';
    msg.innerText = text;
    container.appendChild(msg);
    msg.scrollIntoView({ behavior: 'smooth' });
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
