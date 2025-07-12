# AI Buddy Test Suite Documentation

## Overview

This directory contains the comprehensive test suite for AI Buddy, ensuring reliability and robustness of all components.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── test_monitoring_agent.py # Tests for the core monitoring agent
├── test_conversation_manager.py # Tests for conversation persistence
├── test_file_operations.py  # Tests for file operation handling
├── test_session_manager.py  # Tests for session management
├── test_smart_context.py    # Tests for intelligent context building
├── test_repo_blob_generator.py # Tests for repository analysis
└── fixtures/               # Test data and sample projects
    ├── sample_data.py      # Reusable test data
    └── test_project/       # Sample project structure
```

## Running Tests

### Quick Start

```bash
# Run all tests with coverage
./run_tests.sh

# Run only unit tests
./run_tests.sh unit

# Run only integration tests
./run_tests.sh integration
```

### Manual Testing

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_monitoring_agent.py

# Run tests matching a pattern
pytest -k "test_api_key"

# Run with verbose output
pytest -v

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## Test Categories

Tests are marked with different categories:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests that involve multiple components
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.requires_api` - Tests that need API access (skipped in CI)

## Key Test Fixtures

### Global Fixtures (conftest.py)

- `temp_dir` - Temporary directory for file operations
- `mock_sessions_dir` - Mock sessions directory
- `mock_project_root` - Sample project structure
- `mock_genai_client` - Mocked Gemini API client
- `sample_conversation` - Pre-built conversation history
- `ipc_files` - Inter-process communication file paths

### Module-Specific Fixtures

Each test module may define additional fixtures specific to its needs.

## Testing Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Mock external dependencies

### 2. Clear Test Names
```python
def test_api_key_hot_reload_waits_for_valid_key():
    """Test that monitoring agent waits for valid API key."""
```

### 3. Arrange-Act-Assert Pattern
```python
def test_example():
    # Arrange
    manager = ConversationManager("test_session", "/tmp")
    
    # Act
    manager.add_exchange("Question", "Answer")
    
    # Assert
    assert len(manager.conversation_history) == 1
```

### 4. Mock External Services
```python
@patch('monitoring_agent.genai.Client')
def test_gemini_integration(mock_client):
    mock_client.return_value.models.generate_content.return_value = "Response"
```

## Coverage Goals

- Minimum overall coverage: 80%
- Core modules (monitoring_agent, file_operations): 90%+
- Focus on critical paths and error handling

## Continuous Integration

Tests are automatically run on:
- Every pull request
- Commits to main branch
- Nightly builds

## Adding New Tests

1. Create test file following naming convention: `test_<module>.py`
2. Import necessary fixtures from conftest
3. Group related tests in classes
4. Use descriptive test names
5. Add appropriate markers (@pytest.mark.unit, etc.)
6. Ensure tests are deterministic and fast

## Debugging Failed Tests

```bash
# Run with debugging output
pytest -vv --tb=short

# Drop into debugger on failure
pytest --pdb

# Run last failed tests
pytest --lf

# Run tests that match a specific marker
pytest -m "not slow"
```

## Performance Testing

For performance-critical code:
```python
@pytest.mark.slow
def test_large_context_performance(benchmark):
    result = benchmark(build_large_context, 1000_files)
    assert result.time < 5.0  # Should complete in under 5 seconds
```

## Security Testing

Always test:
- Path traversal prevention
- API key handling
- File permission checks
- Input validation

## Maintenance

- Review and update tests when adding features
- Remove obsolete tests
- Keep fixtures up-to-date
- Monitor test execution time
- Investigate flaky tests immediately