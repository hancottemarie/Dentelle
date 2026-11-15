.PHONY: install-backend dev-backend test

install-backend:
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install --upgrade pip
	backend/.venv/bin/pip install -r backend/requirements.txt

dev-backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && .venv/bin/pytest
