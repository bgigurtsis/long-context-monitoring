# Git hooks

The pre-commit hook checks staged Python files with Ruff and scans staged changes
with Gitleaks. The pre-push hook scans the commit history with Gitleaks.

Enable both hooks once per checkout:

```bash
git config --local core.hooksPath .githooks
```

Install Gitleaks and uv before committing. Dataset exceptions identify only
reviewed synthetic application fixtures and prose false positives by exact
file, rule, and line. They do not disable any detector.

Run `uv run pytest` before committing. Recorded dataset bytes stay outside the
Python lint scope.
