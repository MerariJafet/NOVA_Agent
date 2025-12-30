# NOVA Agent — Architecture Overview

NOVA Agent is a local intelligent assistant built with a modular,
observable, and extensible architecture.

## High-Level Architecture

```ascii
User (Browser)
|
v
React + Vite Frontend
|
| /api/chat
v
FastAPI Backend
|
+--> Intelligent Router
|      |
|      +--> Model Selection
|           (Mixtral / Dolphin)
|
+--> Memory Layer
|      |
|      +--> Episodic Memory (SQLite)
|      +--> Semantic Memory (optional / future)
|
+--> LLM Execution (Ollama)
```

## Key Components

### Intelligent Router
The router analyzes the user prompt and selects the most suitable
model. The routing decision is transparent and returned to the UI.

### Backend (FastAPI)
- Clean API boundary
- Deterministic response schema
- Smoke-tested for stability

### Frontend (React + Vite)
- Real-time chat UI
- Displays router, model, and latency metadata
- Proxied API to avoid CORS issues

### Observability
Each response includes:
- Router used
- Model selected
- Reasoning summary
- Latency in milliseconds

## Design Goals

- Stability over feature count
- Transparency over black-box behavior
- Local-first execution
- Portfolio-grade reproducibility
