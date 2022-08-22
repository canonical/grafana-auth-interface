# grafana-auth-interface

## Developing

You can use the environments created by `tox` for development:

```bash
tox --notest -e unit
source .tox/unit/bin/activate
```

## Testing

### Unit tests

```bash
tox -e unit
```

### Static analysis

```bash
tox -e static
```

### Linting

```bash
tox -e lint
```