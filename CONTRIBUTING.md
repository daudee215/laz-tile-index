# Contributing

Thanks for considering a contribution. Two rules:

1. Open an issue first for non-trivial changes so we can align on scope.
2. Run the full test + lint + type bar locally before opening a PR:

```
uv pip install -e '.[dev]'
ruff check .
mypy --strict src
pytest -q
```

Bug reports should include a minimal LAS/LAZ that reproduces the issue (or
the seed / parameters used to generate it). Avoid attaching point clouds
larger than ~10 MB to the issue body.

PRs that touch the on-disk sidecar schema must include a migration test
that loads the previous schema version and round-trips it.
