# Contributing to AgentShield X

First off, thank you for considering contributing to AgentShield X!

This project is intended as a demonstration of production-quality security engineering for AI agent systems. Contributions that improve security, reliability, or developer experience are welcome.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Be respectful, professional, and constructive.

## How Can I Contribute?

### Reporting Bugs

If you find a bug or security vulnerability, please open an issue describing:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (OS, Python version, Node version)

> **Security Vulnerabilities:** If you find a critical security vulnerability, please do not open a public issue. Instead, review our [Security Policy](SECURITY.md) and email the maintainers directly.

### Suggesting Enhancements

We welcome suggestions for new security engines, AI threat detections, or dashboard features. Please open an issue with the `enhancement` label and describe your idea before writing code.

### Pull Requests

1. Fork the repository and create your branch from `main`.
2. Ensure your code follows the existing style guidelines.
3. Write automated tests for any new behavior. See the [Testing Guide](TESTING.md) for details.
4. Keep changes focused. If you have multiple unrelated changes, submit them as separate PRs.
5. Update documentation (in `docs/` and `README.md`) if your change impacts public APIs or deployment.
6. Provide a clear, descriptive PR title and summary.

## Development Setup

See the [Deployment Guide](docs/DEPLOYMENT.md) for instructions on setting up your local development environment using Docker or local Python/Node instances.

## Architecture

Before making significant changes, please review the [Architecture Documentation](docs/Architecture.md) to understand how the pipeline operates and how the engine singletons interact.

Thank you for contributing!
