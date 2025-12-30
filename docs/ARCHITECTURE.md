# NOVA Agent — Deep Architecture Dive

This document provides a detailed look at the core components of the NOVA Agent system.

## 1. Intelligent Routing (Cerebral Routing)

The Routing layer is the "Brain" of NOVA. It prevents overkill by matching the query complexity to the model capability.

### Decision Flow
1. **Intent Analysis**: The prompt is processed to identify keywords, language, and modal requirements (e.g., "draw", "analyze image", "complex logic").
2. **Model Selection**:
   - **Simple/Speed Tasks**: `dolphin-mistral:7b`.
   - **Complex Reasoning**: `mixtral:8x7b`.
   - **Vision**: `llava:7b` with `moondream:1.8b` as fallback.
3. **Fallback Strategy**: If a high-tier model fails or is unavailable, NOVA automatically falls back to the nearest compatible lightweight model to ensure service continuity.

## 2. Memory Architecture

NOVA uses a hybrid approach to memory to provide both short-term context and long-term personality.

### Episodic Memory (SQLite)
- **Purpose**: Stores the current conversation flow.
- **Implementation**: Uses a local SQLite database (`nova_memory.db`).
- **Data Points**: User messages, Assistant responses, used model, routing reasoning, and extracted facts.

### Semantic Memory (Planned/Internal)
- **Purpose**: Long-term storage of user preferences and global concepts.
- **Future Integration**: Vector database (ChromaDB) for high-dimensional similarity search.

## 3. Tool Calling Flow (Action Layer)

*Note: Fully autonomous tool calling is planned for v2.0.0. Currenly in demo phase.*

1. **Detection**: Router identifies a specific tool name in the prompt (e.g., "search weather").
2. **Validation**: The system checks if the tool is registered in the `AgentRegistry`.
3. **Execution**: The specialized agent (e.g., `ProgrammingAgent`) executes the function.
4. **Final Synthesis**: The result is fed back into the primary model to generate a natural language response.

## 4. Response Caching

To reduce latency for repetitive queries, NOVA implements a semantic-aware cache.

- **Mechanism**: Hashes the prompt and model configuration.
- **Storage**: Key-Value store with TTL (Time To Live).
- **Impact**: Reduces P99 latency from ~2s to <50ms for cache hits.

## 5. Vision Pipeline

1. **Upload**: React frontend sends an image as `multipart/form-data`.
2. **Preprocessing**: FastAPI handles base64 encoding and instruction injection.
3. **Inference**: Ollama runs `llava:7b` to parse the visual context.
4. **Metadata**: The response includes which vision model was used and the total processing time.
