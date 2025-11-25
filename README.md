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

```bash
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
