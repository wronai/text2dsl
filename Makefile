.PHONY: all build test test-cov clean install install-voice lint format docs run voice stop dist upload upload-test publish publish-test help

# Default target
all: build test

# Build the project
build:
	@echo "Building text2dsl..."
	pip install -e .

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ --cov=text2dsl --cov-report=html

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Install all dependencies
install:
	pip install -e ".[all]"
	@if [ ! -f .env ] && [ -f .env.example ]; then cp .env.example .env; fi

# Install only voice dependencies
install-voice:
	pip install -e ".[voice]"

# Run linter
lint:
	flake8 text2dsl/
	mypy text2dsl/

# Format code
format:
	black text2dsl/ tests/

# Build documentation
docs:
	@echo "Documentation available in README.md"

# Run interactive mode
run:
	python -m text2dsl

# Run voice mode
voice:
	python -m text2dsl --voice

stop:
	@if [ -f .text2dsl.pid ]; then \
		pid=$$(cat .text2dsl.pid); \
		if kill -0 $$pid 2>/dev/null; then kill $$pid; fi; \
		rm -f .text2dsl.pid; \
	fi

# Create distribution package
dist:
	python -m build

# Upload to PyPI (test)
upload-test:
	python -m twine upload --repository testpypi dist/*

# Upload to PyPI
upload:
	python -m twine upload dist/*

publish-test: dist upload-test

publish: dist upload

# Show help
help:
	@echo "Available targets:"
	@echo "  all          - Build and test"
	@echo "  build        - Build the project"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  clean        - Clean build artifacts"
	@echo "  install      - Install all dependencies"
	@echo "  stop         - Stop running voice session (uses .text2dsl.pid)"
	@echo "  lint         - Run linters"
	@echo "  format       - Format code"
	@echo "  run          - Run interactive mode"
	@echo "  voice        - Run voice mode"
