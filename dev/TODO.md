# parasolpy TODO

## Release housekeeping



- [ ] Push tags for any already-published PyPI versions (`git push --tags`)
- [ ] Create GitHub Releases for those tags (`gh release create vX.Y.Z --generate-notes`)

## Documentation

- [ ] Add module-level usage snippets (not just the example scripts) to README
- [ ] Write proper docstrings for `reservoir.py` and `ism.py` (currently comment-style)
- [ ] Document expected input CSV / XML formats for the tradeoff explorer CLI
- [ ] Add a CONTRIBUTING.md covering branch / PR conventions

## Code

- [ ] Audit `__init__.py` re-exports against the public API we actually want
- [ ] Add tests (none exist yet) — start with `reservoir.sequent_peak` and `util` conversions
- [ ] Set up CI (GitHub Actions) to run tests on push / PR

## Ideas / later

- [ ] Publish example notebooks alongside the `.py` examples
- [ ] Tag a `0.2.0` once API is stable enough to commit to
