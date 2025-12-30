// main.js - NOVA multimodal interface: text + voice + vision
let currentSessionId = 'webui_' + Date.now();

const els = {
    messagesContainer: () => document.getElementById('messages-container'),
    messageInput: () => document.getElementById('message-input'),
    sendBtn: () => document.getElementById('send-btn')
};

function setupEventListeners() {
    // setupMicFlow() maneja todos los eventos de voz y envío de mensajes
    setupCameraFlow();
    setupMicFlow();
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

document.addEventListener('DOMContentLoaded', () => {
    // Initialize voice modal elements and event listeners
    initVoiceModal();

    if (voiceModeBtn) {
      voiceModeBtn.addEventListener('click', () => {
        console.log('[VOICE] startVoiceSession click');
        startVoiceSession();
      });
    }

    if (voiceStopBtn) {
      voiceStopBtn.addEventListener('click', () => {
        console.log('[VOICE] stopVoiceSession click');
        stopVoiceSession();
      });
    }

    setupEventListeners();
});

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
      const response = await fetch('/api/upload', { method: 'POST', body: formData });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      
      // Mostrar respuesta del modelo
      addMessage('assistant', data.response || '[Respuesta vacía del modelo]');
      
      // Mostrar qué modelo se usó
      if (data.model_used) {
        addMessage('assistant', `🤖 Modelo usado: ${data.model_used}`);
      }
    } catch (e) {
      console.error('upload error', e);
      addMessage('assistant', '⚠️ Hubo un error procesando la imagen. Intenta nuevamente o verifica el modelo de visión.');
    }

    selectedFile = null;
    fileInput.value = '';
    document.getElementById('image-instruction').value = '';
  };

  cancelImageBtn.onclick = () => {
    previewModal.classList.add('hidden');
    selectedFile = null;
    fileInput.value = '';
    document.getElementById('image-instruction').value = '';
  };

  // Agregar event listener para el botón de cerrar
  const closeBtn = document.getElementById('close-modal-btn');
  if (closeBtn) {
    closeBtn.onclick = () => {
      previewModal.classList.add('hidden');
      selectedFile = null;
      fileInput.value = '';
      document.getElementById('image-instruction').value = '';
    };
  }
}

// === MICRÓFONO: PUSH-TO-TALK Y MODO VOZ ACTIVA ===
// Ajustable: tiempo de silencio antes de enviar mensaje completo desde voz.
// Merari prefiere frases largas, por eso usamos 4000ms (4s).
// TODO: se puede subir a 5000–6000ms si ella lo pide.
let silenceMs = 1800; // tiempo base de silencio antes de enviar en voz activa

let recognition = null;
let isAlwaysListening = false;      // toggle de voz continua (ON/OFF)
let isRecording = false;           // indica si SpeechRecognition está grabando ahora mismo
let isManuallyStopping = false;    // true solo cuando el usuario apaga el toggle o hacemos stop explícitamente
let silenceTimer = null;          // timer para detectar silencio
let voiceBuffer = '';             // buffer de texto acumulado en voz activa
let cooldownTimer = null;         // para esperar un poco tras TTS
let isLoading = false;
let isAssistantSpeaking = false;   // true mientras NOVA está reproduciendo audio/TTS
let lastAssistantMessage = '';     // último texto de respuesta de NOVA para filtrar eco
let lastAssistantText = '';        // texto exacto del asistente para comparación avanzada
let cooldownAfterSpeaking = false; // true durante cooldown después de que NOVA termine de hablar

// Voice state machine
const VOICE_STATE = {
  IDLE: 'idle',
  LISTENING: 'listening',
  THINKING: 'thinking',
  SPEAKING: 'speaking',
  READY: 'ready',
  ERROR: 'error'
};
let currentVoiceState = VOICE_STATE.IDLE;
let isProcessingVoice = false; // true while processing a voice request
let lastVoiceRequestHadResponse = false; // tracks if the last voice request got a response
let sendingInProgress = false; // true while sending a voice message to prevent duplicates

// Error types for voice recognition
const fatalErrors = ['not-allowed', 'permission-denied', 'service-not-allowed'];
const softErrors = ['network', 'language-not-supported', 'bad-grammar'];

// Voice modal elements
let voiceModal = null;
let voiceStatusLabel = null;
let voiceTextLabel = null;
let voiceLiveTranscript = null;
let voiceStopBtn = null;
let voiceModeBtn = null; // Nuevo: botón principal de voz

// Función para verificar si el transcript es demasiado similar al último mensaje del asistente
function isTooSimilarToLastAssistant(transcript) {
  if (!lastAssistantText || !transcript) return false;

  const assistantLower = lastAssistantText.toLowerCase();
  const transcriptLower = transcript.toLowerCase();

  // Si el transcript es idéntico al último mensaje del asistente, es eco
  if (assistantLower === transcriptLower) return true;

  // Si el transcript contiene más del 80% del último mensaje del asistente
  if (assistantLower.includes(transcriptLower) && transcriptLower.length > assistantLower.length * 0.8) return true;

  // Verificación de similitud por palabras clave
  const assistantWords = assistantLower.split(/\s+/).filter(word => word.length > 3);
  const transcriptWords = transcriptLower.split(/\s+/).filter(word => word.length > 3);

  if (assistantWords.length === 0 || transcriptWords.length === 0) return false;

  const matchingWords = transcriptWords.filter(word =>
    assistantWords.some(assistantWord =>
      assistantWord.includes(word) || word.includes(assistantWord) ||
      levenshteinDistance(word, assistantWord) <= 2 // Distancia de edición pequeña
    )
  );

  const matchRatio = matchingWords.length / Math.min(assistantWords.length, transcriptWords.length);
  return matchRatio > 0.8; // Si más del 80% de las palabras coinciden, es eco
}

// Función de distancia de Levenshtein para medir similitud entre palabras
function levenshteinDistance(a, b) {
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;

  const matrix = [];
  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }
  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // substitution
          matrix[i][j - 1] + 1,     // insertion
          matrix[i - 1][j] + 1      // deletion
        );
      }
    }
  }

  return matrix[b.length][a.length];
}

// Voice modal management functions
function initVoiceModal() {
  voiceModal = document.getElementById('voice-modal');
  voiceStatusLabel = document.getElementById('voice-status-label');
  voiceTextLabel = document.getElementById('voice-text-label');
  voiceLiveTranscript = document.getElementById('voice-live-transcript');
  voiceStopBtn = document.getElementById('voice-stop-btn');
  voiceModeBtn = document.getElementById('voice-mode-btn');

  // Event listeners se configuran en DOMContentLoaded
}

// Función centralizada para manejar TODOS los estados del modal de voz
function updateVoiceModalState(state, payload = {}) {
  currentVoiceState = state;
  if (!voiceStatusLabel || !voiceTextLabel) return;

  switch (state) {
    case VOICE_STATE.LISTENING:
      voiceStatusLabel.textContent = '🎙️ Escuchando…';
      voiceStatusLabel.style.color = '#00f5ff';
      voiceTextLabel.textContent = 'Estoy capturando lo que dices.';
      break;
    case VOICE_STATE.THINKING:
      voiceStatusLabel.textContent = '🤔 Pensando…';
      voiceStatusLabel.style.color = '#ffd900';
      voiceTextLabel.textContent = 'Procesando tu mensaje, espera un momento.';
      // Limpiar transcript mientras piensa
      if (voiceLiveTranscript) voiceLiveTranscript.textContent = '';
      break;
    case VOICE_STATE.SPEAKING:
      voiceStatusLabel.textContent = '🧠 NOVA está hablando…';
      voiceStatusLabel.style.color = '#ff6fff';
      voiceTextLabel.textContent = 'Escucha la respuesta, luego podrás hablar de nuevo.';
      // Mostrar el texto que NOVA está diciendo
      if (payload.text && voiceLiveTranscript) {
        voiceLiveTranscript.textContent = payload.text;
      }
      break;
    case VOICE_STATE.READY:
      voiceStatusLabel.textContent = '✅ Listo para escuchar de nuevo';
      voiceStatusLabel.style.color = '#00ff95';
      voiceTextLabel.textContent = 'Cuando quieras, puedes decirme otra cosa.';
      break;
    case VOICE_STATE.ERROR:
      voiceStatusLabel.textContent = '⚠️ Problema con la voz';
      voiceStatusLabel.style.color = '#ff9500';
      voiceTextLabel.textContent = payload.message || 'Intenta hablar de nuevo o revisa tu micrófono.';
      if (voiceLiveTranscript) voiceLiveTranscript.textContent = '';
      break;
    default:
      voiceStatusLabel.textContent = '🎤 Voz inactiva';
      voiceStatusLabel.style.color = '#ffffff';
      voiceTextLabel.textContent = '';
      if (voiceLiveTranscript) voiceLiveTranscript.textContent = '';
  }

  // NOTA: El modal NO se muestra/oculta automáticamente aquí.
  // Solo cambia textos, iconos y contenido del cuadro de transcripción.
  // El modal se controla exclusivamente desde startVoiceSession/stopVoiceSession.
}

// Función startVoiceSession: inicia sesión de voz activa
function startVoiceSession() {
  if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
    console.error('SpeechRecognition no soportado');
    updateVoiceModalState(VOICE_STATE.ERROR, { message: 'Tu navegador no soporta reconocimiento de voz.' });
    if (voiceModal) voiceModal.classList.remove('hidden');
    return;
  }

  isAlwaysListening = true;
  isManuallyStopping = false;
  isAssistantSpeaking = false;
  voiceBuffer = '';
  lastAssistantText = '';

  // Actualizar el botón de voz principal para mostrar que está activo
  if (voiceModeBtn) {
    voiceModeBtn.classList.add('active');
    voiceModeBtn.textContent = 'Voz: ACTIVA';
  }

  if (voiceModal) voiceModal.classList.remove('hidden');

  updateVoiceModalState(VOICE_STATE.LISTENING);

  // Initialize recognition if not already done
  if (!recognition) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'es-MX';
    recognition.continuous = true;
    recognition.interimResults = true;

    // Set up event handlers
    recognition.onstart = () => {
      isRecording = true;
      updateVoiceModalState(VOICE_STATE.LISTENING);
      console.log('[VOICE] recognition start');
    };

    recognition.onresult = (event) => {
      console.log('[VOICE] onresult', event);
      // FILTRAR ECO EN TODOS LOS CICLOS - Aplicar filtro anti-eco al inicio
      const now = Date.now();
      if (isAssistantSpeaking || cooldownAfterSpeaking) {
        voiceBuffer = ''; // Limpiar buffer
        if (silenceTimer) clearTimeout(silenceTimer); // Cancelar timer
        if (voiceLiveTranscript) voiceLiveTranscript.textContent = '';
        console.log('Recognition: ignoring results while assistant is speaking or in cooldown');
        return; // No procesar nada si el asistente habla o está en cooldown
      }

      // Extraer SIEMPRE el último resultado; usar interims para mostrar texto en vivo
      const last = event.results[event.results.length - 1];
      const transcript = last[0].transcript.trim().toLowerCase();
      const isFinal = last.isFinal;

      // Filtro de similitud por palabras para frases largas
      if (isTooSimilarToLastAssistant(transcript)) {
        if (voiceLiveTranscript) voiceLiveTranscript.textContent = '';
        voiceBuffer = '';
        if (silenceTimer) clearTimeout(silenceTimer);
        console.log('Recognition: ignoring transcript too similar to last assistant response');
        return;
      }

      // 2. Si transcript contiene partes del último mensaje de NOVA, ignorar
      if (lastAssistantMessage && transcript && lastAssistantMessage.includes(transcript)) {
        console.log('Recognition: ignoring transcript that matches assistant message');
        return;
      }

      // 3. Si transcript coincide con el texto del DOM del último mensaje de NOVA, ignorar
      const lastAssistantDOM = document.querySelector('.message.assistant:last-child .message-content');
      if (lastAssistantDOM) {
        const domText = lastAssistantDOM.innerText.trim().toLowerCase();
        if (domText.includes(transcript)) {
          console.log('Recognition: ignoring transcript that matches DOM content');
          return;
        }
      }

      // 4. Verificación avanzada: si transcript contiene >70% de palabras del último texto del asistente
      if (lastAssistantText) {
        const assistantWords = lastAssistantText.toLowerCase().split(/\s+/);
        const transcriptWords = transcript.split(/\s+/);
        const matchingWords = transcriptWords.filter(word =>
          assistantWords.some(assistantWord => assistantWord.includes(word) || word.includes(assistantWord))
        );
        const matchPercentage = transcriptWords.length > 0 ? (matchingWords.length / transcriptWords.length) * 100 : 0;

        if (matchPercentage > 70) {
          console.log(`Recognition: ignoring transcript with ${matchPercentage.toFixed(1)}% match to assistant text`);
          return;
        }
      }

      // Si pasa todos los filtros, procesar normalmente
      voiceBuffer = transcript;
      const text = voiceBuffer.trim();
      if (!text) return;

      // If we were in READY state, switch to LISTENING when user speaks
      if (currentVoiceState === VOICE_STATE.READY) {
        updateVoiceModalState(VOICE_STATE.LISTENING);
      }

      // Update live transcript in modal - mostrar lo que el usuario está diciendo (interim o final)
      if (voiceLiveTranscript) {
        voiceLiveTranscript.textContent = text;
      }

      // Resetear el timer de silencio cada vez que llega audio nuevo
      if (silenceTimer) clearTimeout(silenceTimer);
      const timeoutMs = isFinal ? 700 : silenceMs; // más ágil cuando Web Speech marca final
      silenceTimer = setTimeout(() => {
        const finalText = voiceBuffer.trim();
        if (!isAlwaysListening) return;           // si ya se apagó el modo, no enviar
        if (!finalText) return;
        if (sendingInProgress) return; // Evitar envíos duplicados

        // Change to THINKING state and clear transcript
        updateVoiceModalState(VOICE_STATE.THINKING);
        if (voiceLiveTranscript) voiceLiveTranscript.textContent = '';

        sendingInProgress = true;
        sendMessageToNova(finalText, { source: 'voice' })
          .catch(() => updateVoiceModalState('error', { message: 'Error al comunicarme con NOVA.' }))
          .finally(() => { sendingInProgress = false; });

        const messageInput = document.getElementById('message-input');
        if (messageInput) messageInput.value = '';
        voiceBuffer = '';
      }, timeoutMs);
    };

    recognition.onerror = (event) => {
      console.error('[VOICE] recognition error:', event.error, event.message);
      const err = event.error;

      if (fatalErrors.includes(err)) {
        isAlwaysListening = false;
        isManuallyStopping = true;
        try { recognition.stop(); } catch (_) {}
        updateVoiceModalState(VOICE_STATE.ERROR);
        const live = document.getElementById('voice-live-transcript');
        if (live) live.textContent = '';
        return;
      }

      if (softErrors.includes(err)) {
        const live = document.getElementById('voice-live-transcript');
        if (live) live.textContent = '';
        if (isAlwaysListening && !isManuallyStopping) {
          // Volvemos a estado de ESCUCHANDO sin mostrar error
          updateVoiceModalState(VOICE_STATE.LISTENING);
          try { recognition.start(); } catch (_) {}
        }
        return;
      }

      // Error 'no-speech' en modo always listening → reintentar sin mostrar error
      if (err === 'no-speech' && isAlwaysListening) {
        console.warn('No speech detectado, reintentando...');
        const live = document.getElementById('voice-live-transcript');
        if (live) live.textContent = '';
        restartRecognitionAfterSpeaking();
        return;
      }

      console.warn('[VOICE] Unknown recognition error treated as soft:', err);
      const live = document.getElementById('voice-live-transcript');
      if (live) live.textContent = '';
      if (isAlwaysListening && !isManuallyStopping) {
        updateVoiceModalState(VOICE_STATE.LISTENING);
        try { recognition.start(); } catch (_) {}
      }
    };

    recognition.onend = () => {
      isRecording = false;
      console.log('[VOICE] recognition end, state=', currentVoiceState, 'assistantSpeaking=', isAssistantSpeaking);

      // Si el usuario apagó el modo voz manualmente, no reiniciar
      if (isManuallyStopping) {
        isManuallyStopping = false;
        updateVoiceModalState(VOICE_STATE.READY);
        return;
      }

      // Si el asistente está hablando, agenda reinicio cuando termine
      if (isAssistantSpeaking) {
        console.log('[VOICE] onend while assistant speaking → schedule restart');
        setTimeout(() => {
          if (!isAssistantSpeaking && isAlwaysListening) {
            restartRecognitionAfterSpeaking();
          }
        }, 600);
        return;
      }

      // Si seguimos en modo voz activa, reiniciar reconocimiento
      if (isAlwaysListening) {
        restartRecognitionAfterSpeaking();
      }
    };
  }

  try {
    recognition.start();
  } catch (err) {
    console.error('Error al iniciar reconocimiento de voz', err);
    updateVoiceModalState(VOICE_STATE.ERROR, { message: 'No pude acceder al micrófono.' });
  }
}

// Función stopVoiceSession: detiene sesión de voz activa
function stopVoiceSession() {
  isAlwaysListening = false;
  isManuallyStopping = true;
  cooldownAfterSpeaking = false; // Reset cooldown

  // Actualizar el botón de voz principal (voice-mode-btn) para mostrar que está inactivo
  if (voiceModeBtn) {
    voiceModeBtn.classList.remove('active');
    voiceModeBtn.textContent = 'Voz: Push';
  }

  if (isRecording && recognition) {
    recognition.stop();
  }

  // Limpiar timers y buffer
  if (silenceTimer) {
    clearTimeout(silenceTimer);
    silenceTimer = null;
  }
  if (cooldownTimer) {
    clearTimeout(cooldownTimer);
    cooldownTimer = null;
  }
  voiceBuffer = '';
  const messageInput = document.getElementById('message-input');
  if (messageInput) messageInput.value = '';

  // Limpiar transcript
  if (voiceLiveTranscript) voiceLiveTranscript.textContent = '';

  if (voiceModal) voiceModal.classList.add('hidden');
}

// Función central para enviar mensajes (movida fuera de setupMicFlow para acceso global)
async function sendMessageToNova(text, options = {}) {
  if (!text.trim() || isProcessingVoice) return;

  isProcessingVoice = true;
  lastVoiceRequestHadResponse = false;

  try {
    console.log('[VOICE] enviando a /api/chat:', text);
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: currentSessionId })
    });

    if (!res.ok) {
      console.error('[VOICE] /api/chat fallo', res.status);
      updateVoiceModalState(VOICE_STATE.ERROR);
      return;
    }

    const data = await res.json();
    console.log('[VOICE] respuesta de NOVA recibida length=', (data.response || '').length);
    console.log('Chat response:', data);
    addMessage('assistant', data.response || '[Sin respuesta]');
    
    // Limpiar input del usuario para evitar mezcla con texto del asistente
    const messageInput = document.getElementById('message-input');
    if (messageInput) messageInput.value = '';
    
    // Guardar último mensaje de NOVA para filtrar eco textual
    lastAssistantMessage = (data.response || '').trim().toLowerCase();
    lastAssistantText = (data.response || '').trim(); // Texto exacto para comparación avanzada

    lastVoiceRequestHadResponse = true;

    // TTS: reproducir respuesta por voz si está disponible y Voz Activa está ON
    if (isAlwaysListening && data.response) {
      // Detener reconocimiento antes de hablar
      updateVoiceModalState(VOICE_STATE.THINKING);
      isAssistantSpeaking = false;
      clearTimeout(silenceTimer);
      if (recognition && recognition.abort) recognition.abort();
      playAssistantAudio(data.response);
    } else {
      // If not using TTS, go back to listening
      updateVoiceModalState(VOICE_STATE.LISTENING);
      if (voiceLiveTranscript) voiceLiveTranscript.textContent = '';
    }
    
  } catch (err) {
    console.error('Error llamando /api/chat:', err);
    updateVoiceModalState(VOICE_STATE.ERROR);
    addMessage('assistant', '⚠️ Error al comunicarme con NOVA. Verifica tu conexión e intenta de nuevo.');
  } finally {
    isProcessingVoice = false;
  }
}

// Estados de carga (movida fuera para acceso global)
function setLoading(loading) {
  isLoading = loading;
  const loadingStatus = document.getElementById('loading-status');
  const messageInput = document.getElementById('message-input');
  const sendBtn = document.getElementById('send-btn');
  const micBtn = document.getElementById('mic-btn');

  if (loadingStatus) {
    if (loading) {
      loadingStatus.classList.remove('hidden');
    } else {
      loadingStatus.classList.add('hidden');
    }
  }

  // Deshabilitar input y botones durante carga O durante Voz Activa
  const shouldDisable = loading || isAlwaysListening;
  if (messageInput) messageInput.disabled = shouldDisable;
  if (sendBtn) sendBtn.disabled = shouldDisable;
  if (micBtn) micBtn.disabled = loading; // El mic solo se deshabilita durante carga
}

function speakResponse(text) {
  if (!('speechSynthesis' in window)) {
    console.warn('[TTS] speechSynthesis no soportado');
    updateVoiceModalState(VOICE_STATE.READY);
    restartRecognitionAfterSpeaking();
    return;
  }

  // Limpia cualquier cola anterior para evitar solapes
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'es-ES';  // Español
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  console.log('[TTS] hablando:', text.slice(0, 80));

  isAssistantSpeaking = true;
  lastAssistantText = text;
  updateVoiceModalState(VOICE_STATE.SPEAKING, { text });
  const live = document.getElementById('voice-live-transcript');
  if (live) live.textContent = text;  // mostrar respuesta mientras habla

  utterance.onstart = () => {
    console.log('[TTS] onstart');
  };

  utterance.onerror = (event) => {
    console.error('[TTS] error:', event.error);
    isAssistantSpeaking = false;
    updateVoiceModalState(VOICE_STATE.READY);
    restartRecognitionAfterSpeaking();
  };

  utterance.onend = () => {
    console.log('[TTS] onend');
    isAssistantSpeaking = false;
    restartRecognitionAfterSpeaking();
  };

  window.speechSynthesis.speak(utterance);
}

// Nueva función playAssistantAudio con límites de longitud ampliados
function playAssistantAudio(text) {
  if (!('speechSynthesis' in window)) {
    console.warn('[TTS] speechSynthesis no soportado');
    updateVoiceModalState(VOICE_STATE.READY);
    restartRecognitionAfterSpeaking();
    return;
  }

  // Limpiar cualquier cola anterior
  window.speechSynthesis.cancel();

  // Aumentar el tamaño máximo del texto que se manda a TTS para que no corte respuestas largas
  const MAX_TTS_CHARS = 2800; // ~triple de lo anterior
  let ttsText = text;
  if (ttsText.length > MAX_TTS_CHARS) {
    ttsText = ttsText.slice(0, MAX_TTS_CHARS) + '…';
  }

  // Dejar SIEMPRE el texto COMPLETO en el chat principal, sólo recortar para la voz
  console.log(`[TTS] Reproduciendo respuesta de ${text.length} caracteres (TTS limitado a ${MAX_TTS_CHARS})`);

  isAssistantSpeaking = true;
  lastAssistantText = text; // Guardar texto completo para filtros anti-eco
  updateVoiceModalState(VOICE_STATE.SPEAKING, { text: text }); // Mostrar texto completo en modal

  // Mostrar texto completo en el modal (ya es scrollable)
  const live = document.getElementById('voice-live-transcript');
  if (live) live.textContent = text;

  const utterance = new SpeechSynthesisUtterance(ttsText);
  utterance.lang = 'es-ES';
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  utterance.onstart = () => {
    console.log(`[TTS] Reproduciendo TTS de ${ttsText.length} caracteres`);
  };

  utterance.onerror = (event) => {
    console.error('[TTS] Error en TTS:', event.error);
    isAssistantSpeaking = false;
    updateVoiceModalState(VOICE_STATE.READY);
    restartRecognitionAfterSpeaking();
  };

  utterance.onend = () => {
    console.log('[TTS] TTS completado');
    isAssistantSpeaking = false;
    restartRecognitionAfterSpeaking();
  };

  window.speechSynthesis.speak(utterance);
}

// Función para reiniciar reconocimiento después de que NOVA termine de hablar
function restartRecognitionAfterSpeaking() {
  clearTimeout(cooldownTimer);
  if (!isAlwaysListening || !recognition) return;

  console.log('[VOICE] Reiniciando reconocimiento después de hablar');
  updateVoiceModalState(VOICE_STATE.READY);

  cooldownTimer = setTimeout(() => {
    if (!isAlwaysListening) return; // Verificar nuevamente antes de reiniciar

    try {
      console.log('[VOICE] Iniciando reconocimiento nuevamente');
      recognition.start();
      updateVoiceModalState(VOICE_STATE.LISTENING);
    } catch (e) {
      console.error('Error al reiniciar reconocimiento después de hablar:', e);
      // Intentar nuevamente después de un breve delay
      setTimeout(() => {
        if (isAlwaysListening) {
          try {
            recognition.start();
            updateVoiceModalState(VOICE_STATE.LISTENING);
          } catch (retryError) {
            console.error('Error en reintento de reconocimiento:', retryError);
          }
        }
      }, 1000);
    }
  }, 1200); // pequeña pausa para que no capture su propia voz
}

function setupMicFlow(){
  // Initialize voice modal
  initVoiceModal();

  const sendBtn = document.getElementById('send-btn');
  const messageInput = document.getElementById('message-input');

  // Integrar con el envío normal de mensajes
  if (sendBtn) {
    sendBtn.onclick = () => {
      const text = messageInput.value.trim();
      if (text && !isLoading) {
        sendMessageToNova(text);
        messageInput.value = '';
        voiceBuffer = ''; // Limpiar buffer si había algo
      }
    };
  }

  if (messageInput) {
    messageInput.onkeydown = (e) => {
      if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
        e.preventDefault();
        sendBtn.click();
      }
    };
  }
}
