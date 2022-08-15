# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""grafana-auth interface library.
This library implements the grafana-auth relation interface, it contains the Requires and Provides classes for handling
the interface.
This library is designed to allow charms to configure authentication to Grafana, 
the provider will set the authentication mode that it needs and will pass the necessary configuration of that authentication mode.
The requirer will consume the authentication configuration to authenticate to Grafana.

## Getting Started
From a charm directory, fetch the library using `charmcraft`:
```shell
charmcraft fetch-lib charms.grafana_auth_interface.v0.grafana_auth_interface
```
You will also need to add the following library to the charm's `requirements.txt` file:
- jsonschema

### Provider charm
Example:
```python
from charms.grafana_auth_interface.v0.grafana_auth_interface import GrafanaAuthProvides
from ops.charm import CharmBase
class ExampleProviderCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.grafana_auth = GrafanaAuthProvides(
            self,
            relationship_name='grafana_auth'
            auth_type='proxy', 
            header_name="X-WEBAUTH-USER",
            header_property="username",
            auto_sign_up=False,
        )
        self.framework.observe(
            self.grafana_auth.on.grafana_url_available, self._on_grafana_url_available
        )
```
### Requirer charm
Example:
```python
from charms.grafana_auth_interface.v0.grafana_auth_interface import GrafanaAuthRequires
from ops.charm import CharmBase
class ExampleRequirerCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.grafana_auth = GrafanaAuthRequires(
            self,
            relationship_name="grafana_auth",
            grafana_url="https://grafana.example.com/"
        )
        self.framework.observe(
            self.grafana_auth.on.grafana_auth_config_available, self._on_grafana_auth_config_available
        )
```
"""
import json
import logging
from jsonschema import exceptions, validate  # type: ignore[import]
from ops.framework import EventBase, EventSource, Object
from ops.charm import (
    CharmBase,
    CharmEvents,
    RelationChangedEvent,
    RelationJoinedEvent,
)

# The unique Charmhub library identifier, never change it
LIBID = "bd7d0356fdc74c65bb206be3b843fbfa"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

PROVIDER_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "$id": "https://canonical.github.io/charm-relation-interfaces/grafana_auth/schemas/provider.json",
    "type": "object",
    "title": "`grafana_auth` provider schema",
    "description": "The `grafana_auth` root schema comprises the entire provider databag for this interface.",
    "default": {},
    "examples": [
        {
            "application-data": {
                "auth": {
                    "proxy": {
                        "enabled": True,
                        "header_name": "some-header",
                        "header_property": "some-header-property",
                        "auto_sign_up": False,
                        "sync_ttl": 36200,
                        "whitelist": [
                            "localhost",
                            "canonical.com"
                        ],
                        "headers": [
                            "some-header",
                            "some-other-header"
                        ],
                        "headers_encoded": True,
                        "enable_login_token": True
                    }
                }
            }
        }
    ],
    "required": [
        "application-data"
    ],
    "properties": {
        "application-data": {
            "$id": "#/properties/application-data",
            "title": "Application Databag",
            "type": "object",
            "additionalProperties": True,
            "required": [
                "auth"
            ],
            "properties": {
                "auth": {
                    "additionalProperties": True,
                    "anyOf": [
                        {
                            "required": [
                                "proxy"
                            ]
                        }
                    ],
                    "type": "object",
                    "properties": {
                        "proxy": {
                            "$id": "#/properties/application-data/proxy",
                            "type": "object",
                            "required": [
                                "header_name",
                                "header_property"
                            ],
                            "additionalProperties": True,
                            "properties": {
                                "enabled": {
                                    "$id": "#/properties/application-data/proxy/enabled",
                                    "type": "boolean",
                                    "default": True
                                },
                                "header_name": {
                                    "$id": "#/properties/application-data/proxy/header_name",
                                    "type": "string"
                                },
                                "header_property": {
                                    "$id": "#/properties/application-data/proxy/header_property",
                                    "type": "string"
                                },
                                "auto_sign_up": {
                                    "$id": "#/properties/application-data/proxy/auto_sign_up",
                                    "type": "boolean",
                                    "default": True
                                },
                                "sync_ttl": {
                                    "$id": "#/properties/application-data/proxy/sync_ttl",
                                    "type": "integer",
                                    "default": 60
                                },
                                "whitelist": {
                                    "$id": "#/properties/application-data/proxy/whitelist",
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "headers": {
                                    "$id": "#/properties/application-data/proxy/headers",
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "headers_encoded": {
                                    "$id": "#/properties/application-data/proxy/headers_encoded",
                                    "type": "boolean",
                                    "default": False
                                },
                                "enable_login_token": {
                                    "$id": "#/properties/application-data/proxy/enable_login_token",
                                    "type": "boolean",
                                    "default": False
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "additionalProperties": True
}

REQUIRER_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "$id": "https://canonical.github.io/charm-relation-interfaces/interfaces/grafana_auth/schemas/requirer.json",
    "type": "object",
    "title": "`grafana_auth` requirer schema",
    "description": "The `grafana_auth` root schema comprises the entire consumer databag for this interface.",
    "default": {},
    "examples": [
        {
            "application-data": {
                "url": "https://grafana.example.com/"
            }
        }
    ],
    "required": [
        "application-data"
    ],
    "properties": {
        "application-data": {
            "$id": "#/properties/application-data",
            "title": "Application Databag",
            "type": "object",
            "additionalProperties": True,
            "required": [
                "url"
            ],
            "url": {
                "$id": "#/properties/application-data/url",
                "type": "string"
            }
        }
    },
    "additionalProperties": True
}

logger = logging.getLogger(__name__)

def _load_relation_data(raw_relation_data: dict) -> dict:
    """Loads relation data from the relation data bag.
    Json loads all data.
    Args:
        raw_relation_data: Relation data from the databag
    Returns:
        dict: Relation data in dict format.
    """
    relation_data_dict = dict()
    for key in raw_relation_data:
        try:
            relation_data_dict[key] = json.loads(raw_relation_data[key])
        except json.decoder.JSONDecodeError:
            relation_data_dict[key] = raw_relation_data[key]
    return relation_data_dict


class GrafanaUrlAvailableEvent(EventBase):
    """Charm event triggered when provider charm extracts grafana url from relation data"""

    def __init__(self, handle, grafana_url: dict, relation_id: int):
        super().__init__(handle)
        self.grafana_url = grafana_url
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "grafana_url": self.grafana_url,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.grafana_url = snapshot["grafana_url"]
        self.relation_id = snapshot["relation_id"]


class GrafanaAuthProviderCharmEvents(CharmEvents):
    """List of events that the grafana auth provider charm can leverage."""

    grafana_url_available = EventSource(GrafanaUrlAvailableEvent)

class GrafanaAuthProvides(Object):
    """Grafana authentication configuration provider class to be initialized by grafana-auth providers"""

    on = GrafanaAuthProviderCharmEvents()

    def __init__(self, charm: CharmBase, relationship_name: str, auth_type: str, **kwargs):
        super().__init__(charm, relationship_name)
        self._charm = charm
        self._relationship_name = relationship_name
        self._auth_conf = self._build_conf_dict(auth_type, **kwargs)
        self.framework.observe(
            charm.on[relationship_name].relation_joined, self._set_auth_config_in_relation_data
        )
        self.framework.observe(
            charm.on[relationship_name].relation_changed, self._on_grafana_auth_relation_changed
        )

    def _build_conf_dict(self, auth_type, **kwargs) -> dict:
        """Builds a dictionary for grafana authentication that matches the json schema of the provider.
        Args:
            auth_type (str): authentication type to be set in the configuration dict.
            kwargs: key and value pairs provided to configure authentication mode.
        Returns:
            dict: Authentication configuration as a dictionary.
        """
        conf_dict = dict()
        conf_dict["auth"]= {auth_type:{ key:value for key, value in kwargs.items()}}
        return conf_dict

    def _set_auth_config_in_relation_data(self, event: RelationJoinedEvent) -> None:
        """Handler triggered on relation joined event. Adds authentication config to relation data.
        Args:
            event: Juju event
        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return
        grafana_auth_relation = self.model.get_relation(
            relation_name=self._relationship_name, relation_id=event.relation.id
        )
        relation_data = event.relation.data[event.app]
        relation_data_dict = _load_relation_data(relation_data)
        current_auth_conf = relation_data_dict.get("grafana_auth")
        if not current_auth_conf:
            relation_data["grafana_auth"] = json.dumps(self._auth_conf)

    def _on_grafana_auth_relation_changed(self,event: RelationChangedEvent) -> None:
        """Handler triggered on relation changed events. 
        Extracts grafana url from relation data and emits grafana_url_available event
        Args:
            event: Juju event
        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return
        relation_data = _load_relation_data(event.relation.data[event.app])
        if not relation_data:
            logger.info("No relation data")
            return
        grafana_url = relation_data.get("grafana_url")
        if not grafana_url:
            logger.warning("No Grafana url")
            return
        if not self._app_relation_data_is_valid(grafana_url):
            logger.warning("Relation data did not pass JSON Schema validation")
            return
        self.on.grafana_url_available.emit(grafana_url=grafana_url)

    @staticmethod
    def _app_relation_data_is_valid(app_relation_data) -> bool:
        """Uses JSON schema validator to authentication configuration content.
        Args:
            auth_conf (str): authentication configuration set by the provider charm.
        Returns:
            bool: True/False depending on whether the configuration follows the json schema.
        """
        relation_data = {"application-data" : app_relation_data}
        try:
            validate(instance=relation_data, schema=REQUIRER_JSON_SCHEMA)
            return True
        except exceptions.ValidationError:
            return False


class AuthConfAvailableEvent(EventBase):
    """Charm Event triggered when Authentication config is ready."""

    def __init__(self, handle, auth_conf: dict, relation_id: int):
        super().__init__(handle)
        self.auth_conf = auth_conf
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "auth_conf": self.auth_conf,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.auth_conf = snapshot["auth_conf"]
        self.relation_id = snapshot["relation_id"]


class AuthConfRevokedEvent(EventBase):
    """Charm event triggered when the auth config set by this relation is revoked"""

    def __init__(self, handle, revoked_auth_modes: list, relation_id: int):
        super().__init__(handle)
        self.revoked_auth_modes = revoked_auth_modes
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "revoked_auth_modes": self.revoked_auth_modes,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.revoked_auth_modes = snapshot["revoked_auth_modes"]
        self.relation_id = snapshot["relation_id"]


class GrafanaAuthRequirerCharmEvents(CharmEvents):
    """List of events that the grafana auth requirer charm can leverage."""

    grafana_auth_config_available = EventSource(AuthConfAvailableEvent)
    grafana_auth_config_revoked = EventSource(AuthConfRevokedEvent)


class GrafanaAuthRequires(Object):
    """Grafana authentication configuration requirer class to be initialized by grafana-auth requirers"""

    on = GrafanaAuthRequirerCharmEvents()

    def __init__(self, charm, relationship_name: str, grafana_url: str):
        super().__init__(charm, relationship_name)
        self._charm = charm
        self._relationship_name = relationship_name
        self._grafana_url = {"url": grafana_url}
        self.framework.observe(
            charm.on[relationship_name].relation_changed, self._on_grafana_auth_relation_changed
        )
        self.framework.observe(
            charm.on[relationship_name].relation_joined, self._set_grafana_url_in_relation_data
        )

    def _on_grafana_auth_relation_changed(self, event) -> None:
        """Handler triggered on relation changed events.
        Args:
            event: Juju event
        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return
        relation_data = _load_relation_data(event.relation.data[event.app])
        if not relation_data:
            logger.info("No relation data")
            return
        auth_conf = relation_data.get("grafana_auth")
        if not auth_conf:
            logger.warning("No authentication config")
            return
        if not self._app_relation_data_is_valid(auth_conf):
            logger.warning("Relation data did not pass JSON Schema validation")
            return
        self.on.grafana_auth_config_available.emit(auth_conf=auth_conf)

    def _set_grafana_url_in_relation_data(self, event: RelationJoinedEvent) -> None:
        """Handler triggered on relation joined events. Adds Grafana URL to relation data. 
        Args:
            event: Juju event
        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return
        grafana_auth_relation = self.model.get_relation(
            relation_name=self._relationship_name, relation_id=event.relation.id
        )
        relation_data = event.relation.data[event.app]
        relation_data["grafana_url"] = json.dumps(self._grafana_url)

    @staticmethod
    def _app_relation_data_is_valid(app_relation_data) -> bool:
        """Uses JSON schema validator to authentication configuration content.
        Args:
            auth_conf (str): authentication configuration set by the provider charm.
        Returns:
            bool: True/False depending on whether the configuration follows the json schema.
        """
        relation_data = {"application-data" : app_relation_data}
        try:
            validate(instance=relation_data, schema=PROVIDER_JSON_SCHEMA)
            return True
        except exceptions.ValidationError:
            return False
