PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
UVICORN ?= uvicorn
APP_MODULE ?= src.app.main:app

.PHONY: install run format lint test clean deploy-remote

install:
	$(PIP) install -r requirements.txt

run:
	PYTHONPATH=. $(UVICORN) $(APP_MODULE) --host $${HOST:-0.0.0.0} --port $${PORT:-8000} --reload

format:
	$(PYTHON) -m black src

lint:
	ruff check src

test:
	pytest -q

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +

# Remote deploy via SSH (expects SSH_HOST, SSH_USER, APP_DIR set)
deploy-remote:
	@if [ -z "$$SSH_HOST" ] || [ -z "$$SSH_USER" ] || [ -z "$$APP_DIR" ]; then \
		echo "Set SSH_HOST, SSH_USER, APP_DIR env vars"; exit 1; \
	fi
	ssh $$SSH_USER@$$SSH_HOST "bash -lc 'cd $$APP_DIR && bash scripts/deploy.sh'"
