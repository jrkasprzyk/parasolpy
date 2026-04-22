# Releasing

This document describes how to cut a new release of `parasolpy` using [Poetry](https://python-poetry.org/).

## Prerequisites

- Poetry installed (`pipx install poetry` or see the [official docs](https://python-poetry.org/docs/#installation)).
- A clean working tree on `main` with all changes to be released already merged.
- A [PyPI](https://pypi.org/) account with upload rights for `parasolpy`, and an API token.

## One-time setup (per machine)

Configure Poetry with your PyPI API token (stored in Poetry's config, not committed):

```bash
poetry config pypi-token.pypi <your-pypi-token>
```

For testing against TestPyPI first (recommended):

```bash
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi <your-testpypi-token>
```

### Releasing from a new computer

Poetry stores tokens locally (e.g. `%APPDATA%\pypoetry\auth.toml` on Windows,
`~/.config/pypoetry/auth.toml` on macOS/Linux) and does not sync them between
machines. On a new computer you need to run the `poetry config pypi-token.*`
commands above again. You can either:

- **Reuse an existing token** if you saved it in a password manager when it was
  created (PyPI only displays the token value once, so if you didn't save it,
  you can't retrieve it).
- **Generate a new token** at <https://pypi.org/manage/account/token/>. Using
  a per-machine token is good hygiene — if a machine is lost you can revoke
  just that token without affecting the others.

### About token scopes

When you create a token on PyPI you choose its scope:

- **Account-scoped token** — works for all your PyPI projects and can create
  new ones. Convenient but higher blast radius if leaked.
- **Project-scoped token** — tied to a single existing project (e.g. just
  `parasolpy`). Cannot upload to other projects or create new ones. Safer, and
  the recommended default for ongoing releases.

A common pattern: use an account-scoped token once to perform the very first
upload of a new project (project-scoped tokens can't create projects), then
replace it with a project-scoped token for all subsequent releases.

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

4. **Update `CHANGELOG.md`.** Move everything under the `[Unreleased]`
   heading to a new `[X.Y.Z] — YYYY-MM-DD` section (using the version you
   just set and today's date). Leave an empty `[Unreleased]` heading at the
   top for future changes, and update the link references at the bottom of
   the file:

   ```markdown
   ## [Unreleased]

   ## [0.2.0] — 2026-05-01
   ...

   [Unreleased]: https://github.com/jrkasprzyk/parasolpy/compare/v0.2.0...HEAD
   [0.2.0]: https://github.com/jrkasprzyk/parasolpy/releases/tag/v0.2.0
   ```

5. **Commit the version bump and changelog together.**

   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "Release $(poetry version -s)"
   ```

6. **Tag the release.**

   ```bash
   git tag "v$(poetry version -s)"
   ```

7. **Build the distributions.** This creates the wheel and sdist in `dist/`.

   ```bash
   poetry build
   ```

8. **(Optional) Publish to TestPyPI first** and verify the upload looks right:

   ```bash
   poetry publish -r testpypi
   ```

   Try installing from TestPyPI in a throwaway environment to sanity-check:

   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ parasolpy
   ```

9. **Publish to PyPI.**

   ```bash
   poetry publish
   ```

   Or combine build and publish in one step:

   ```bash
   poetry publish --build
   ```

10. **Push the commit and tag to GitHub.** `poetry publish` only uploads to
   PyPI — it does not touch GitHub. Plain `git push` pushes commits but *not*
   tags, so you need both commands:

   ```bash
   git push
   git push --tags
   ```

   Verify the tag made it to the remote:

   ```bash
   git ls-remote --tags origin
   ```

11. **Create a GitHub Release.** Pushing a tag makes it show up under the
    repo's "Tags" view, but it will *not* appear under "Releases" until you
    explicitly create a release from the tag. Use either:

    - **Web UI:** Repo → Releases → "Draft a new release" → select the tag →
      add release notes → Publish release.
    - **GitHub CLI** (if `gh` is installed):

      ```bash
      gh release create "v$(poetry version -s)" --generate-notes
      ```

      `--generate-notes` auto-populates release notes from commits and PRs
      merged since the previous tag.

    Confirm the release is live:

    ```bash
    gh release list
    ```

### Troubleshooting: release on PyPI but not on GitHub

This almost always means one of:

- The tag was never pushed (`git push --tags` was skipped). Fix with
  `git push --tags`.
- The tag was pushed but no GitHub Release was created from it. Fix by
  running `gh release create "v$(poetry version -s)" --generate-notes` or
  creating the release in the web UI.

## Rolling back a failed release

PyPI does not allow re-uploading the same version. If a release is broken:

1. Yank the bad version on PyPI (via the web UI) if already published.
2. Bump to the next patch version and repeat the release steps.
