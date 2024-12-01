# Contributing to IRS Tax Form Parser

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Request Process

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/irs-tax-form-parser.git
cd irs-tax-form-parser

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Install pre-commit hooks
pre-commit install

# Download required models
python -m spacy download en_core_web_sm
```

### Code Style

- We use [Black](https://black.readthedocs.io/) for code formatting
- We use [flake8](https://flake8.pycqa.org/) for linting
- We use [mypy](http://mypy-lang.org/) for type checking

Run these tools before submitting:

```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type check
mypy src
```

### Testing

We use pytest for testing. Please write tests for any new functionality:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_ocr_parser.py
```

### Commit Message Convention

We follow the [Conventional Commits](https://conventionalcommits.org/) specification:

- `feat:` A new feature
- `fix:` A bug fix
- `docs:` Documentation only changes
- `style:` Changes that do not affect the meaning of the code
- `refactor:` A code change that neither fixes a bug nor adds a feature
- `test:` Adding missing tests or correcting existing tests
- `chore:` Changes to the build process or auxiliary tools

Examples:
```
feat: add support for Form 1099-K processing
fix: correct SSN validation regex pattern
docs: update installation instructions for Windows
test: add unit tests for NLP processor validation
```

## Bug Reports

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/your-org/irs-tax-form-parser/issues).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Feature Requests

We welcome feature requests! Please:

1. Check if the feature already exists or is planned
2. Open an issue with a clear description of the feature
3. Explain the use case and why it would be valuable
4. Consider contributing the implementation yourself!

## Security Issues

Please do not report security vulnerabilities through public GitHub issues. Instead, please email us at security@your-org.com.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in our README and release notes. Thank you for helping make this project better!

## Areas Where We Need Help

- **Form Types**: Adding support for additional IRS forms
- **OCR Accuracy**: Improving text extraction from low-quality documents
- **Validation Rules**: Enhancing data validation for different form types
- **Performance**: Optimizing processing speed for large batches
- **Documentation**: Improving user guides and API documentation
- **Testing**: Expanding test coverage and adding integration tests
- **Internationalization**: Adding support for multiple languages

## Getting Help

- Check the [documentation](README.md)
- Search [existing issues](https://github.com/your-org/irs-tax-form-parser/issues)
- Ask questions in [GitHub Discussions](https://github.com/your-org/irs-tax-form-parser/discussions)
- Join our community chat (link to be added)

Thank you for contributing! 🎉