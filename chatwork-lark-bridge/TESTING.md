# Testing Guide - Chatwork-Lark Bridge

Complete guide for testing the bidirectional message synchronization system.

## 📋 Table of Contents

- [Test Overview](#test-overview)
- [Test Setup](#test-setup)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [Continuous Integration](#continuous-integration)

---

## 🎯 Test Overview

### Test Pyramid

The project follows the test pyramid approach with three layers:

```
         /\
        /E2E\      ← 10% - Full system flows
       /------\
      /  INT  \    ← 30% - API endpoints
     /----------\
    /   UNIT    \  ← 60% - Individual components
   /--------------\
```

### Test Statistics

| Category | Count | Coverage Target |
|----------|-------|----------------|
| **Unit Tests** | 50+ | 80%+ |
| **Integration Tests** | 20+ | 70%+ |
| **E2E Tests** | 5+ | Critical paths |
| **Total** | 75+ tests | 80%+ overall |

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (API endpoints)
- `@pytest.mark.e2e` - End-to-end tests (full workflows)
- `@pytest.mark.slow` - Tests that take >1 second
- `@pytest.mark.redis` - Tests requiring Redis connection

---

## 🛠️ Test Setup

### 1. Install Test Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r requirements-test.txt
```

**Test Dependencies:**
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `fakeredis` - Redis mocking
- `respx` - HTTP mocking
- `faker` - Test data generation

### 2. Environment Configuration

Tests use the `conftest.py` setup which automatically configures test environment variables. No manual `.env` file needed for testing.

### 3. Redis Setup (Optional)

Most tests use `fakeredis` and don't require a real Redis instance. For tests marked with `@pytest.mark.redis`, you can:

**Option A: Use fakeredis (default)**
```bash
# No setup needed - tests use fakeredis automatically
pytest
```

**Option B: Use real Redis (optional)**
```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Run Redis-dependent tests
pytest -m redis
```

---

## 🚀 Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_config.py

# Run specific test function
pytest tests/unit/test_config.py::TestSettings::test_settings_load_from_env

# Run tests by marker
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m e2e          # Only E2E tests
pytest -m "not slow"   # Exclude slow tests
```

### Coverage Reports

```bash
# Run tests with coverage
pytest --cov=src

# Generate HTML coverage report
pytest --cov=src --cov-report=html
# View at: htmlcov/index.html

# Show missing lines
pytest --cov=src --cov-report=term-missing

# Fail if coverage below 80%
pytest --cov=src --cov-fail-under=80
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4

# Auto-detect CPU count
pytest -n auto
```

### Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
ptw

# With specific args
ptw -- -v -m unit
```

---

## 📊 Test Coverage

### Current Coverage

Run coverage report to see current metrics:

```bash
pytest --cov=src --cov-report=term-missing
```

### Coverage Targets by Module

| Module | Target | Priority |
|--------|--------|----------|
| `src/core/` | 90%+ | Critical |
| `src/services/` | 85%+ | High |
| `src/api/` | 80%+ | High |
| `src/utils/` | 85%+ | Medium |

### Viewing Coverage Reports

```bash
# Generate HTML report
pytest --cov=src --cov-report=html

# Open in browser (Windows)
start htmlcov/index.html

# Open in browser (Linux/Mac)
open htmlcov/index.html
```

---

## 📁 Test Structure

### Directory Layout

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
│
├── unit/                    # Unit tests (60%)
│   ├── __init__.py
│   ├── test_config.py       # Configuration tests
│   ├── test_exceptions.py   # Exception tests
│   ├── test_retry.py        # Retry logic tests
│   ├── test_webhook_verification.py
│   ├── test_redis_client.py
│   └── test_message_processor.py
│
├── integration/             # Integration tests (30%)
│   ├── __init__.py
│   ├── test_chatwork_api.py # Chatwork webhook endpoint
│   └── test_lark_api.py     # Lark webhook endpoint
│
└── e2e/                     # E2E tests (10%)
    ├── __init__.py
    └── test_bidirectional_flow.py  # Full message flows
```

### Test Files

Each module has a corresponding test file:

- `src/core/config.py` → `tests/unit/test_config.py`
- `src/services/redis_client.py` → `tests/unit/test_redis_client.py`
- `src/api/chatwork.py` → `tests/integration/test_chatwork_api.py`

---

## ✍️ Writing Tests

### Unit Test Example

```python
import pytest
from src.core.exceptions import RetryableError

@pytest.mark.unit
class TestRetryableError:
    """Test retryable error functionality."""

    def test_creation(self):
        """Test creating retryable error."""
        error = RetryableError("Temporary failure", {"retry": 1})

        assert error.message == "Temporary failure"
        assert error.details["retry"] == 1
        assert isinstance(error, BridgeException)

    def test_string_representation(self):
        """Test error string representation."""
        error = RetryableError("Test error")

        assert str(error) == "Test error"
```

### Integration Test Example

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.integration
class TestChatworkWebhook:
    """Test Chatwork webhook endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_success(self, async_client, fake_redis):
        """Test successful webhook processing."""
        # Setup
        await fake_redis.setex("room:chatwork:12345", 86400, "oc_test")

        # Mock external service
        with patch("src.api.chatwork.message_processor") as mock:
            mock.process_chatwork_message = AsyncMock(return_value="om_123")

            # Execute
            response = await async_client.post(
                "/webhook/chatwork",
                json=payload,
                headers=headers
            )

            # Assert
            assert response.status_code == 200
            mock.process_chatwork_message.assert_called_once()
```

### E2E Test Example

```python
@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteMessageFlow:
    """Test complete message synchronization."""

    @pytest.mark.asyncio
    async def test_chatwork_to_lark_flow(self, async_client, fake_redis):
        """Test Chatwork → Lark message flow."""
        # 1. Setup
        await fake_redis.setex("room:chatwork:123", 86400, "oc_lark")

        # 2. Send Chatwork webhook
        response = await async_client.post("/webhook/chatwork", ...)
        assert response.status_code == 200

        # 3. Verify message was synced
        mapping = await fake_redis.get("msg:chatwork:999")
        assert mapping is not None

        # 4. Verify loop prevention
        # (send back to Chatwork, should be blocked)
```

### Using Fixtures

```python
@pytest.mark.unit
class TestRedisClient:
    """Test Redis client."""

    @pytest.mark.asyncio
    async def test_save_mapping(self, redis_client):
        """Test saving message mapping."""
        # redis_client fixture provides fake Redis instance
        await redis_client.save_message_mapping(
            "chatwork", "999", "lark", "om_123"
        )

        mapping = await redis_client.get_message_mapping("chatwork", "999")
        assert mapping["target_message_id"] == "om_123"
```

### Test Data

Use fixtures from `conftest.py` for consistent test data:

```python
def test_webhook_processing(self, chatwork_webhook_data):
    """Use pre-defined test data."""
    # chatwork_webhook_data fixture provides valid webhook payload
    assert chatwork_webhook_data["webhook_event_type"] == "message_created"
```

---

## 🎯 Test Scenarios

### Critical Test Scenarios

#### 1. Loop Prevention Tests

```python
# Scenario: Chatwork → Lark → (blocked) → Chatwork
# Scenario: Lark → Chatwork → (blocked) → Lark
# Scenario: Duplicate message ID detection
```

**Files:**
- `tests/e2e/test_bidirectional_flow.py::test_loop_prevention_*`
- `tests/unit/test_message_processor.py::test_loop_detection`

#### 2. Webhook Signature Verification

```python
# Scenario: Valid signature
# Scenario: Invalid signature
# Scenario: Tampered request body
# Scenario: Wrong secret
```

**Files:**
- `tests/unit/test_webhook_verification.py`
- `tests/integration/test_chatwork_api.py::test_invalid_signature`

#### 3. Error Handling & Retry

```python
# Scenario: Retryable error recovery
# Scenario: Non-retryable error immediate failure
# Scenario: Rate limit handling
# Scenario: Retry exhaustion
```

**Files:**
- `tests/unit/test_retry.py`

#### 4. Message Mapping

```python
# Scenario: Bidirectional room mapping
# Scenario: Missing room mapping
# Scenario: Message ID tracking (Redis)
# Scenario: TTL expiration
```

**Files:**
- `tests/unit/test_redis_client.py`
- `tests/unit/test_message_processor.py`

---

## 🔧 Debugging Tests

### Run Single Test with Debug Output

```bash
# Verbose output
pytest tests/unit/test_config.py::test_settings_load_from_env -v

# Show print statements
pytest tests/unit/test_config.py -s

# Show local variables on failure
pytest tests/unit/test_config.py -l

# Drop into debugger on failure
pytest tests/unit/test_config.py --pdb
```

### Check Test Collection

```bash
# Show all tests that would run
pytest --collect-only

# Show tests matching pattern
pytest --collect-only -k "chatwork"
```

### Log Output

```bash
# Show log output during tests
pytest --log-cli-level=DEBUG

# Capture warnings
pytest -W default
```

---

## 🔄 Continuous Integration

### GitHub Actions Workflow

`.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-commit Hooks

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest tests/unit -m unit
        language: system
        pass_filenames: false
        always_run: true
```

---

## 📈 Test Metrics

### Measuring Test Quality

```bash
# Test execution time
pytest --durations=10

# Slowest tests
pytest --durations=0 | grep -E "slow|SLOW"

# Coverage per file
pytest --cov=src --cov-report=term-missing
```

### Quality Checklist

- [ ] All tests pass: `pytest`
- [ ] Coverage ≥ 80%: `pytest --cov=src --cov-fail-under=80`
- [ ] No warnings: `pytest -W error`
- [ ] Fast execution: Unit tests < 0.1s each
- [ ] Isolated: Tests don't depend on order
- [ ] Deterministic: Tests pass consistently

---

## 🐛 Common Issues

### Issue 1: Redis Connection Error

**Problem:** Tests fail with "Connection refused" to Redis

**Solution:**
```python
# Use fakeredis (default) - no real Redis needed
# Tests use fake_redis fixture automatically
```

### Issue 2: Async Test Not Running

**Problem:** `RuntimeWarning: coroutine 'test_xxx' was never awaited`

**Solution:**
```python
# Add @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result == expected
```

### Issue 3: Mock Not Working

**Problem:** Real API is being called instead of mock

**Solution:**
```python
# Use full import path in patch
with patch("src.services.message_processor.LarkClient") as mock:
    # Not: patch("src.services.lark_client.LarkClient")
    mock.return_value = AsyncMock()
```

### Issue 4: Fixture Not Found

**Problem:** `fixture 'xxx' not found`

**Solution:**
- Check `conftest.py` has the fixture
- Verify `conftest.py` is in test directory or parent
- Check fixture scope matches test requirements

---

## 📚 Additional Resources

### Pytest Documentation
- [Pytest Docs](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Pytest-cov](https://pytest-cov.readthedocs.io/)

### Testing Best Practices
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Mocking Guide](https://realpython.com/python-mock-library/)

---

## ✅ Quick Reference

### Run All Tests
```bash
pytest
```

### Run Specific Test Category
```bash
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m e2e           # E2E tests only
```

### Coverage Report
```bash
pytest --cov=src --cov-report=html
```

### Debug Mode
```bash
pytest -v -s --pdb
```

### CI Mode (strict)
```bash
pytest --cov=src --cov-fail-under=80 -W error
```

---

**Testing Version:** 1.0.0
**Last Updated:** 2025-12-31
**Maintainer:** Claude (Anthropic)
