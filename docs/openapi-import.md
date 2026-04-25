# OpenAPI Import

Loadwright can generate a starter spec from an OpenAPI 3.x document.

```bash
bin/loadwright import openapi examples/openapi/petstore-lite.yaml -o /tmp/petstore-loadwright.yaml
```

Override the target server:

```bash
bin/loadwright import openapi openapi.yaml --base-url https://staging.example.com -o loadwright.yaml
```

## What Gets Imported

- `servers[0].url` becomes `target`.
- Each supported operation becomes one request.
- `operationId` becomes the request name when present.
- Path parameters become Loadwright variables.
- Query parameters become request query values.
- JSON request bodies get a basic example body from examples or schema properties.
- The first `2xx` response becomes the expected status.

## Current Limitations

- OpenAPI 3.x only.
- `$ref` resolution is not implemented yet.
- Security schemes are not imported yet.
- Imported specs are starter specs and should be reviewed before CI use.
