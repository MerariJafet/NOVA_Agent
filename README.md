<<<<<<< HEAD
# 🧠 NOVA Agent (v0.1.0-stable-demo)

> **Intelligent Agentic System with Cerebral Routing and Hybrid Architecture.**
=======
# NOVA Agent - Multimodal AI Assistant

NOVA es un asistente de IA multimodal que combina capacidades de texto, voz y visión en una interfaz cyberpunk elegante. Soporta chat conversacional, análisis de imágenes, Push-to-Talk y modo de escucha activa continua.

## ✨ Características

- **🗣️ Voz Interactiva**: Push-to-Talk y modo de escucha activa continua
- **👁️ Análisis de Imágenes**: Sube imágenes y obtén análisis detallados con instrucciones personalizadas
- **💬 Chat Inteligente**: Conversaciones fluidas con modelos de lenguaje avanzados
- **🎨 UI Cyberpunk**: Interfaz moderna con tema cyberpunk y animaciones
- **📊 Dashboard**: Métricas en tiempo real y visualizaciones con Chart.js
- **🔧 API REST**: Endpoints completos para integración
- **🚀 Fácil Despliegue**: Comando simple para iniciar/detener

## 🛠️ Instalación

### Prerrequisitos

- Python 3.8+
- Ollama instalado y corriendo
- Modelos requeridos: `llava:7b`, `moondream` (fallback), `dolphin-mistral:7b`, `mixtral:8x7b`

### Instalación Rápida
>>>>>>> feature/sprint4-2-multimodal

NOVA is a portfolio-ready demonstration of a local AI agent system that dynamically selects the best LLM for a given task ("Cerebral Routing"), manages episodic memory, and provides a polished React/Vite UI.

## Demo

![NOVA Agent Demo](docs/demo.png)

## Architecture

A high-level overview of the system architecture is available here:
[ARCHITECTURE.md](ARCHITECTURE.md)

## 🚀 Key Features
- **Cerebral Routing**: Automatically routes queries to the most efficient model (e.g., Mixtral for complex logic, Dolphin for speed/code, Moondream for vision).
- **Transparent Metadata**: The UI exposes the decision-making process (Router, Model, Reason, Latency) for every response.
- **Stable Architecture**: FastAPI backend + React/Vite frontend with robust error handling and type safety.
- **Local Privacy**: Designed to run with local LLMs via Ollama.

## 🏗️ Architecture

```ascii
[User Interface] <---> [Vite Proxy] <---> [FastAPI Backend]
(React + Tailwind)                          |
                                            v
                                   [Intelligent Router]
                                   /        |         \
                              [Complex]  [Coding]   [Vision]
                              (Mixtral)  (Dolphin) (Moondream)
```

## 🛠️ Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- **Ollama** running locally (port 11434).

### 1. Backend
```bash
<<<<<<< HEAD
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install stable dependencies
pip install -r requirements.txt

# Start the intelligent backend (on port 8000)
python nova.py start
```

### 2. Frontend
Open a new terminal:
```bash
cd nova-webui

# Install dependencies
npm install

# Start the UI (on port 5173)
npm run dev
```
Open **http://localhost:5173** and try asking: *"Explain quantum computing"* or *"Write a python script for fibonacci"*.

## 🗺️ Roadmap
- [x] **v0.1.0**: Stable MVP with Intelligent Routing & React UI.
- [ ] **v0.2.0**: Specialized Agents (Code, Data, Manager).
- [ ] **v0.3.0**: Semantic Memory (Vector Embeddings) & Long-term Recall.
- [ ] **v0.4.0**: Tool Use (Web Search, File I/O).

## 🧪 Verification
Run the included smoke tests to verify logic without heavy models:
```bash
pytest tests/test_smoke.py -v
```

---
*Version: v0.1.0-stable-demo*
```
=======
# Clonar el repositorio
git clone <repository-url>
cd NOVA_Agent

# Instalar dependencias
pip install -r requirements.txt

# Instalar modelos de Ollama (requiere ~10GB de espacio)
ollama pull llava:7b
ollama pull moondream
ollama pull dolphin-mistral:7b
ollama pull mixtral:8x7b

# Iniciar NOVA
python3 nova.py start
```

## 🚀 Uso

### Interfaz Web

1. Abre `http://localhost:8003` en tu navegador
2. **Chat de Texto**: Escribe mensajes y presiona Enter o el botón enviar
3. **Voz Push-to-Talk**: Mantén presionado el botón del micrófono para hablar
4. **Modo Voz Activa**: Activa el botón verde para escucha continua
5. **Análisis de Imágenes**:
   - Haz clic en el botón de cámara
   - Selecciona una imagen
   - Agrega instrucciones personalizadas (opcional)
   - Envía para análisis

### CLI

```bash
# Iniciar servidor
python3 nova.py start

# Detener servidor
python3 nova.py stop

# Ver estado
python3 nova.py status
```

## 📡 API Endpoints

### Chat
```http
POST /api/chat
Content-Type: application/json

{
  "message": "Hola, ¿cómo estás?",
  "session_id": "usuario_123"
}
```

### Análisis de Imágenes
```http
POST /api/upload
Content-Type: multipart/form-data

file: <imagen>
session_id: usuario_123
message: "Describe esta imagen en detalle"
```

### Métricas
```http
GET /api/metrics/full
```

### Estado del Sistema
```http
GET /api/status
```

## 🤖 Modelos Soportados

### Visión
- **Primario**: `llava:7b` - Análisis de imágenes de alta calidad
- **Fallback**: `moondream` - Modelo ligero alternativo

### Texto
- **Primario**: `dolphin-mistral:7b` - Chat conversacional
- **Avanzado**: `mixtral:8x7b` - Tareas complejas

## 🎯 Requisitos del Sistema

- **RAM**: 16GB mínimo, 32GB recomendado
- **GPU**: Recomendado para modelos de visión (4GB+ VRAM)
- **Almacenamiento**: ~10GB para modelos
- **Navegador**: Chrome/Edge/Firefox con soporte Web Speech API

## 🏗️ Arquitectura

```
nova/
├── api/routes.py      # Endpoints FastAPI
├── core/launcher.py   # Gestión de procesos
├── webui/            # Interfaz frontend
│   ├── index.html    # UI principal
│   ├── main.js       # Lógica cliente
│   ├── styles.css    # Tema cyberpunk
│   └── charts.js     # Dashboard
└── config/           # Configuraciones
```

## 🔧 Configuración

Los modelos y configuraciones se definen en `config/model_profiles.json`:

```json
{
  "vision": {
    "primary": "llava:7b",
    "fallback": "moondream"
  },
  "text": {
    "primary": "dolphin-mistral:7b",
    "advanced": "mixtral:8x7b"
  }
}
```

## 🐛 Solución de Problemas

### Problemas Comunes

1. **Modelo no encontrado**: Asegúrate de que Ollama esté corriendo y los modelos estén descargados
2. **Puerto ocupado**: Verifica que el puerto 8003 esté disponible
3. **Voz no funciona**: Verifica permisos de micrófono en el navegador
4. **Imágenes no se procesan**: Verifica que el modelo de visión esté disponible

### Logs

Los logs se guardan en `logs/` con información detallada para debugging.

## 📈 Desarrollo

### Estructura del Proyecto

- `nova.py`: CLI principal
- `nova/api/routes.py`: API backend
- `nova/webui/`: Frontend completo
- `tests/`: Suite de pruebas

### Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature
3. Agrega tests para cambios nuevos
4. Envía un pull request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

---

**NOVA Agent** - Tu asistente multimodal cyberpunk 🤖✨
>>>>>>> feature/sprint4-2-multimodal
