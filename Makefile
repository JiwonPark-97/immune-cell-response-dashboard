.PHONY: setup pipeline dashboard test

PYTHON ?= python

setup:
	$(PYTHON) -m pip install -r requirements.txt
	npm --prefix frontend ci

pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) analysis.py

dashboard:
	npm --prefix frontend run build
	$(PYTHON) -m uvicorn api:app --host 0.0.0.0 --port $${PORT:-8000}

test:
	$(PYTHON) -m unittest discover -s tests -v
