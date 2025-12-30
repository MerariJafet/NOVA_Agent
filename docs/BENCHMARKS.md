# NOVA Agent — Benchmarks & Performance Metrics

This document outlines how to measure NOVA's performance and the current baseline results.

## 1. Reproduce Benchmarks

Use the provided script to measure latency and routing accuracy.

```bash
# Install benchmark dependencies
pip install -r requirements.txt

# Run the benchmark suite
python scripts/benchmark_latency.py --samples 50 --model dolphin-mistral:7b
```

## 2. Methodology

### Latency Measurement
- **E2E Latency**: Measured from request start to JSON response received.
- **Generation Latency**: Measured purely for the LLM token generation (via Ollama API).
- **Network Overhead**: Calculated as `E2E - Generation`.

### Routing Accuracy
Measured against a "Gold Set" of 50 labeled prompts.
- **Precision**: How many "Mixtral" prompts were correctly routed to Mixtral.
- **Recall**: How many "Simple" prompts were correctly handled by Dolphin.

## 3. Baseline Results (TBD)

*Hardware: Intel i7 / 32GB RAM / NVIDIA RTX 3060*

| Component | P50 Latency | P90 Latency |
|-----------|-------------|-------------|
| **Chat (Dolphin)** | TBD | TBD |
| **Chat (Mixtral)** | TBD | TBD |
| **Vision (LLaVA)** | TBD | TBD |
| **Cache Hit** | TBD | TBD |

---
> [!NOTE]
> Metrics are updated on every major release. Baseline results for v1.0.0 will be populated after final validation.
