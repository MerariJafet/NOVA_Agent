# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-30

### Added
- **Multimodal capabilities**: Full support for vision analysis (LLaVA) and voice (PTT/Active Listening).
- **Cerebral Routing**: Second-generation intelligent router with better model matching.
- **CI Pipeline**: Automated testing, linting, and formatting via GitHub Actions.
- **Improved Documentation**: High-fidelity Mermaid diagrams and detailed architecture deep-dives.
- **Benchmark Suite**: Reproducible performance measurement scripts.

### Changed
- Refactored backend for better process management and PID tracking.
- Standardized API JSON schema for more observable responses.
- Consolidated repository structure and cleaned up legacy backups.

### Fixed
- Fixed CORS issues between React/Vite and FastAPI.
- Resolved memory leakage in episodic facts extraction.
- Fixed startup failure when Ollama models were partially downloaded.

## [0.1.0] - 2025-12-30

### Added
- Initial stable demo with Cerebral Routing baseline.
- Basic React/Vite UI with metadata panel.
- Smoke tests and installation scripts.
