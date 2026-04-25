# Release Checklist

Loadwright releases are created by pushing a semantic version tag. Do not cut a tag until the checklist below is complete.

## Before Tagging

- Confirm `main` is green in GitHub Actions.
- Run the local quality gate:

```bash
go test ./...
go vet ./...
actionlint
goreleaser check
goreleaser release --snapshot --clean --skip=publish
```

- Build and smoke-test the CLI:

```bash
go build -o bin/loadwright ./cmd/loadwright
bin/loadwright version
bin/loadwright compile examples/api/basic.yaml -o /tmp/loadwright-basic.jmx
```

- Run one real JMeter smoke test against a known endpoint and inspect `summary.json`:

```bash
bin/loadwright run examples/api/query-params.yaml --out-dir results/release-smoke --ci
```

- Confirm docs and examples match the released behavior.
- Update `CHANGELOG.md` with the release date and notable changes.

## Tagging

```bash
git tag v0.1.0
git push origin v0.1.0
```

Pushing the tag triggers `.github/workflows/release.yml`, which publishes GitHub release artifacts and GHCR images.

## After Tagging

- Confirm the GitHub Release has archives for macOS, Linux, and Windows.
- Confirm `checksums.txt` exists.
- Confirm the container image exists in GHCR.
- Run a downloaded binary with `loadwright version`.
- Create a follow-up issue for anything deferred from the release.
