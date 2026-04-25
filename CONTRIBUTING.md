# Contributing

Thanks for helping improve jmeterx.

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
go build -o bin/jmeterx ./cmd/jmeterx
```

## Project Direction

jmeterx is spec-driven first. New runtime behavior should normally start as a documented YAML spec change, then compile to deterministic JMX.

AI features are welcome only when they produce reviewable specs, explanations, or suggestions. Normal runs must not require AI.
