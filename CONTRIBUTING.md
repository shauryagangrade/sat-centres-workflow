# Contributing to sat-centres-workflow

Thank you for taking the time to contribute! 🎉

## Ways to Contribute

- **Bug reports** — file an issue using the Bug Report template
- **Feature requests** — file an issue using the Feature Request template
- **Pull requests** — see the workflow below

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-fork>/sat-centres-workflow.git
cd sat-centres-workflow

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies (including dev tools)
pip install -r requirements.txt

# 4. Run the tests
pytest tests/ -v
```

## Code Style

This project uses **black**, **isort**, **ruff**, and **mypy**. Format before committing:

```bash
black .
isort .
ruff check .
mypy .
```

## Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Code is formatted (`black .` / `isort .` / `ruff check .`)
- [ ] Type checks pass (`mypy .`)
- [ ] CHANGELOG.md updated under `## [Unreleased]`
- [ ] PR description explains *what* and *why*

## Branch Naming

| Type | Pattern |
|------|---------|
| Bug fix | `fix/<short-description>` |
| Feature | `feat/<short-description>` |
| Docs | `docs/<short-description>` |
| Chore | `chore/<short-description>` |

## Commit Style

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add overpass provider fallback
fix: handle missing latitude in validator
docs: update geocoding section in README
```

## Reporting Security Issues

**Do not open a public issue for security vulnerabilities.**  
Email **shauryagangrade11@gmail.com** instead. See [SECURITY.md](SECURITY.md) for details.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful.
