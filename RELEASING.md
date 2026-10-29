# Releasing

Releases are published to PyPI by GitHub Actions when a version tag is pushed, with PyPI trusted
publishing: no PyPI token exists. Each release waits for a maintainer's approval in GitHub.

1. Update `__version__` in `src/vaartix/_version.py` and move the "Unreleased" notes in
   `CHANGELOG.md` under the new version. Merge that to `main` through a pull request.
2. Create a GitHub release with the tag `v<version>` (for example `v0.2.0`) on `main`.
3. **Actions** → **Publish to PyPI** → **Review deployments** → **Approve**. The workflow checks
   the tag matches the version, runs the tests on every supported Python, builds and publishes
   with attestations.

## One-time setup (done once by a maintainer)

- pypi.org → your account → **Publishing** → **Add a new pending publisher** → GitHub:
  project name `vaartix`, owner `vaartix-mail`, repository `vaartix-python`, workflow
  `publish.yml`, environment `pypi`.
- GitHub → **Settings** → **Environments** → `pypi`: required reviewer (a maintainer), deployment
  tags `v*` only.
