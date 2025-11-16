# Contributing to Curio

Thank you for your interest in contributing to Curio! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/curio.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit with clear messages: `git commit -m "Add: description of changes"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

### Using DevContainer (Recommended)

1. Open the project in VSCode
2. Click "Reopen in Container" when prompted
3. The environment will be automatically configured

### Manual Setup

See [README.md](README.md#development) for manual setup instructions.

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints
- Format with Black: `black .`
- Lint with pylint: `pylint app/`

### TypeScript/React (Frontend)

- Follow ESLint rules
- Use functional components with hooks
- Format with Prettier
- Use TypeScript for all new code

## Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Commit Messages

Follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Example: `feat: add support for Atom feeds`

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Request review from maintainers
6. Address review feedback
7. Squash commits if requested

## Feature Requests

Open an issue with:
- Clear description of the feature
- Use cases
- Potential implementation approach
- Any relevant examples

## Bug Reports

Include:
- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Environment details (OS, Docker version, etc.)

## Areas for Contribution

- **Features**: New feed types, export options, mobile app
- **UI/UX**: Design improvements, accessibility
- **Documentation**: Tutorials, examples, translations
- **Testing**: Unit tests, integration tests, E2E tests
- **Performance**: Optimization, caching strategies
- **Security**: Security audits, vulnerability fixes

## Questions?

Feel free to open a discussion or contact the maintainers.

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to make Curio better!
