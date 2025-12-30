# 🧠 NOVA Agent (v0.1.0-stable-demo)

> **Intelligent Agentic System with Cerebral Routing and Hybrid Architecture.**

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
