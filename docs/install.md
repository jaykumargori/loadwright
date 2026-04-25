# Install

Loadwright can be installed from source today. Tagged releases will publish binaries, checksums, and container images.

## Go Install

```bash
go install github.com/devaryakjha/loadwright/cmd/loadwright@latest
```

For a specific version:

```bash
go install github.com/devaryakjha/loadwright/cmd/loadwright@v0.1.0
```

## Build From Source

```bash
go build -o bin/loadwright ./cmd/loadwright
bin/loadwright version
```

## GitHub Releases

Release artifacts are produced for:

- macOS arm64 and amd64
- Linux arm64 and amd64
- Windows amd64

Each release includes `checksums.txt`.

## Docker

The container image is useful for compile/import/report workflows that do not need to start Dockerized JMeter from inside the container.

```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" ghcr.io/devaryakjha/loadwright:latest compile examples/api/basic.yaml
```

Running load tests from inside the container requires a Docker strategy that will be documented separately.
