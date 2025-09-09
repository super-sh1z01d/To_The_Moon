PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
UVICORN ?= uvicorn
APP_MODULE ?= src.app.main:app

.PHONY: install run format lint test clean

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
