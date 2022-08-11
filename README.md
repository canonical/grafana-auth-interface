# grafana-auth-interface

## Description

This project contains libraries for the grafana-auth relationship. It contains both the provider and the requirer side of them.

> Note: The charm located here is a placeholder charm and should not packed nor should be deployed.

## Usage

This library can be used by any charm requiring or providing this interface. From the charm's
root directory, run:

```bash
charmcraft fetch-lib charms.grafana_auth_interface.v0.grafana_auth_interface
```

## Relations

```bash
juju relate <grafana-auth provider charm> <grafana-auth requirer charm>
```
