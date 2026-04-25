# Contributing

Thanks for helping improve Loadwright.

## Development

Requirements:

- Go 1.22+
- Docker for integration runs

Run tests:

```bash
go test ./...
```

Build the CLI:

```bash
go build -o bin/loadwright ./cmd/loadwright
```

## Project Direction

loadwright is spec-driven first. New runtime behavior should normally start as a documented YAML spec change, then compile to deterministic JMX.

AI features are welcome only when they produce reviewable specs, explanations, or suggestions. Normal runs must not require AI.

## Attribution

The initial experimental prototype that inspired Loadwright was built by [Jay Kumar Gori](https://github.com/jaykumargori). Public contributors should keep attribution intact in README-facing project materials.
