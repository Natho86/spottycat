.PHONY: help install install-dev test test-unit test-integration test-cov clean lint format check-format setup-dev

# Default target
help:
	@echo "Available commands:"
	@echo "  install       Install package in production mode"
	@echo "  install-dev   Install package in development mode with all dependencies"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  test-cov      Run tests with coverage report"
	@echo "  test-fast     Run fast tests only (exclude slow tests)"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code with black and isort"
	@echo "  check-format  Check code formatting without changing files"
	@echo "  clean         Clean up temporary files and caches"
	@echo "  setup-dev     Set up development environment"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e .[dev]

setup-dev: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything works."

# Testing
test:
	pytest

test-unit:
	pytest tests/unit/ -m unit

test-integration:
	pytest tests/integration/ -m integration

test-cov:
	pytest --cov=spottycat --cov-report=html --cov-report=term

test-fast:
	pytest -m "not slow"

test-aws:
	pytest -m aws

test-mock:
	pytest -m mock

test-cli:
	pytest -m cli

test-config:
	pytest -m config

test-cost:
	pytest -m cost

# Code quality
lint:
	flake8 spottycat tests
	mypy spottycat

format:
	black spottycat tests
	isort spottycat tests

check-format:
	black --check spottycat tests
	isort --check-only spottycat tests

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf coverage.xml
	rm -rf pytest-results.xml

# Development utilities
check: test lint
	@echo "All checks passed!"

ci: clean install-dev test-cov lint
	@echo "CI pipeline completed successfully!"

# Configuration validation
validate-config:
	python -c "import yaml; yaml.safe_load(open('config/default_config.yaml')); print('default_config.yaml is valid')"
	python -c "import yaml; yaml.safe_load(open('config/example_config.yaml')); print('example_config.yaml is valid')"

# Show test structure
show-tests:
	tree tests/ || find tests/ -type f -name "*.py" | sort 