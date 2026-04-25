# Data Sources

Loadwright supports CSV data sources through JMeter's `CSVDataSet`.

```yaml
data:
  users:
    file: users.csv
    recycle: true
    stop_thread: false
    sharing: all
```

When `variables` is omitted, Loadwright reads the CSV header row.

```csv
username,password
alice,alice-secret
bob,bob-secret
```

Use CSV columns as JMeter runtime variables:

```yaml
body:
  username: ${username}
  password: ${password}
```

## Options

- `file`: required CSV path.
- `variables`: optional explicit variable names. Defaults to the CSV header.
- `recycle`: whether JMeter should recycle rows at EOF. Defaults to `true`.
- `stop_thread`: whether JMeter should stop the thread at EOF. Defaults to `false`.
- `sharing`: one of `all`, `thread`, or `group`. Defaults to `all`.

## Example

```bash
bin/loadwright run examples/api/csv-users.yaml --ci
```
