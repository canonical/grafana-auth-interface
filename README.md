# grafana-auth-interface

## Description

This project contains libraries for the grafana-auth relationship. It contains both the provider and the requirer sides.

> Warning: The charm located here is a placeholder charm and should not be packed nor deployed.

## Usage

This library can be used by any charm requiring or providing this interface. From the charm's
root directory, run:

```bash
charmcraft fetch-lib charms.grafana_auth_interface.v0.grafana_auth_interface
```

Add the following libraries to the charm's `requirements.txt` file:
- jsonschema

## Relations

```bash
juju relate <grafana-auth provider charm> <grafana-auth requirer charm>
```
