# AI Buddy Makefile

.PHONY: help install install-dev test test-unit test-integration test-coverage clean lint format run

# Default target
help:
	@echo "AI Buddy Development Commands"
	@echo "============================"
	@echo "make install      - Install production dependencies"
	@echo "make install-dev  - Install development dependencies"
	@echo "make test         - Run all tests"
	@echo "make test-unit    - Run unit tests only"
	@echo "make test-integration - Run integration tests only"
	@echo "make test-coverage - Run tests with coverage report"
	@echo "make lint         - Run code linting"
	@echo "make format       - Format code with black"
	@echo "make clean        - Clean up generated files"
	@echo "make run          - Start AI Buddy"

# Installation targets
install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt

# Testing targets
test:
	pytest -v

test-unit:
	pytest -v -m unit

test-integration:
	pytest -v -m integration

test-coverage:
	pytest -v --cov=. --cov-report=term-missing --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Code quality targets
lint:
	flake8 . --exclude=venv,.venv,tests/fixtures --max-line-length=100
	mypy . --ignore-missing-imports

format:
	black . --exclude="venv|.venv|tests/fixtures"
	isort . --skip venv --skip .venv

# Clean targets
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf sessions/*.tmp sessions/*.log sessions/*.json 2>/dev/null || true

# Run target
run:
	@echo "Starting AI Buddy..."
	@echo "This would normally start the application"
	@echo "For now, use the start-buddy-session.sh script"