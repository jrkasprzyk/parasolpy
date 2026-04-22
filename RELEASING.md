# Releasing

This document describes how to cut a new release of `parasolpy` using [Poetry](https://python-poetry.org/).

## Prerequisites

- Poetry installed (`pipx install poetry` or see the [official docs](https://python-poetry.org/docs/#installation)).
- A clean working tree on `main` with all changes to be released already merged.
- A [PyPI](https://pypi.org/) account with upload rights for `parasolpy`, and an API token.

## One-time setup

Configure Poetry with your PyPI API token (stored in Poetry's config, not committed):

```bash
poetry config pypi-token.pypi <your-pypi-token>
```

For testing against TestPyPI first (recommended):

```bash
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi <your-testpypi-token>
```

## Release steps

1. **Sync and verify the working tree is clean.**

   ```bash
   git checkout main
   git pull
   git status
   ```

2. **Install dependencies and run any checks.**

   ```bash
   poetry install
   ```

3. **Bump the version.** Use Poetry's `version` command with `patch`, `minor`, or `major` (or pass an explicit version).

   ```bash
   poetry version patch      # 0.0.2 -> 0.0.3
   # or: poetry version minor
   # or: poetry version 0.1.0
   ```

   Confirm the new version:

   ```bash
   poetry version
   ```

4. **Commit the version bump.**

   ```bash
   git add pyproject.toml
   git commit -m "Bump version to $(poetry version -s)"
   ```

5. **Tag the release.**

   ```bash
   git tag "v$(poetry version -s)"
   ```

6. **Build the distributions.** This creates the wheel and sdist in `dist/`.

   ```bash
   poetry build
   ```

7. **(Optional) Publish to TestPyPI first** and verify the upload looks right:

   ```bash
   poetry publish -r testpypi
   ```

   Try installing from TestPyPI in a throwaway environment to sanity-check:

   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ parasolpy
   ```

8. **Publish to PyPI.**

   ```bash
   poetry publish
   ```

   Or combine build and publish in one step:

   ```bash
   poetry publish --build
   ```

9. **Push the commit and tag.**

   ```bash
   git push
   git push --tags
   ```

10. **Create a GitHub release** for the pushed tag with release notes summarizing changes.

## Rolling back a failed release

PyPI does not allow re-uploading the same version. If a release is broken:

1. Yank the bad version on PyPI (via the web UI) if already published.
2. Bump to the next patch version and repeat the release steps.
