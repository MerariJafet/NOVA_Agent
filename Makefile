.PHONY: backend frontend test help

help:
	@echo "NOVA Agent Dev Commands:"
	@echo "  make backend   - Start backend server independent process"
	@echo "  make frontend  - Start frontend server independent process"
	@echo "  make test      - Run smoke tests"

backend:
	bash scripts/dev_backend.sh

frontend:
	bash scripts/dev_frontend.sh

test:
	./venv/bin/pytest tests/test_smoke.py -v
