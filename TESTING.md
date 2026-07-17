# QA Testing Guide

This document outlines the testing architecture for AgentShield and provides instructions for running the automated test suite.

---

## Overview

AgentShield uses `pytest` as its primary testing framework. The testing suite is divided into two main categories:
1. **Core Unit Tests:** Isolated tests for individual engines (Detection, Trust, Behavior, Decision, Replay) and utilities (JWT).
2. **API Integration Tests:** End-to-end tests for the FastAPI router endpoints (Auth, Analyze, Health, WebSocket).

---

## Directory Structure

```
backend/tests/
├── pytest.ini                 # Pytest configuration
├── .coveragerc                # Coverage configuration
├── api/                       # Integration & API tests
│   ├── test_analyze_api.py    # Pipeline orchestration tests
│   ├── test_auth_api.py       # JWT endpoint tests
│   ├── test_health_api.py     # Liveness probe tests
│   └── test_websocket.py      # Real-time event streaming tests
└── core/                      # Unit tests
    ├── test_behavior_dna.py   # Statistical baseline tests
    ├── test_decision_engine.py# Aggregation & logic tests
    ├── test_detector.py       # Threat signature regex tests
    ├── test_jwt.py            # Authentication & cryptography tests
    ├── test_replay_engine.py  # Forensic session tests
    └── test_trust_engine.py   # Trust scoring & poisoning tests
```

---

## Running the Tests

Ensure you are in the `backend/` directory and your virtual environment is active.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio httpx
```

### 2. Run the Full Suite
To execute all tests and generate a coverage report in the terminal:
```bash
pytest
```

### 3. Run Specific Categories
**Run only unit tests:**
```bash
pytest tests/core/
```

**Run only API tests:**
```bash
pytest tests/api/
```

**Run a specific test file:**
```bash
pytest tests/api/test_analyze_api.py
```

### 4. Generate HTML Coverage Report
To view line-by-line coverage in your browser:
```bash
pytest --cov=app --cov-report=html
```
Open `htmlcov/index.html` in your web browser.

---

## Adding New Tests

When contributing new engines or features to AgentShield, please adhere to the following QA guidelines:
1. **Naming:** All test files must start with `test_`.
2. **Fixtures:** Use `pytest.fixture` for engine initialization rather than creating global instances.
3. **Mocking:** Avoid mocking database/state layers unless strictly necessary. The in-memory engines are designed to be extremely fast and should be tested with real instances.
4. **Coverage Threshold:** All new core logic must have >90% statement coverage.
