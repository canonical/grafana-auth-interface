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
            self.grafana_auth.on.url_available, self._on_url_available
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
                        "header_name": "X-WEBAUTH-USER",
                        "header_property": "username",
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


class UrlAvailableEvent(EventBase):
    """Charm event triggered when provider charm extracts the url from relation data"""

    def __init__(self, handle, url: str, relation_id: int):
        super().__init__(handle)
        self.url = url
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "url": self.url,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.url = snapshot["url"]
        self.relation_id = snapshot["relation_id"]


class AuthProviderCharmEvents(CharmEvents):
    """List of events that the auth provider charm can leverage."""

    url_available = EventSource(UrlAvailableEvent)

class GrafanaAuthProvides(Object):
    """Grafana authentication configuration provider class to be initialized by grafana-auth providers"""

    on = AuthProviderCharmEvents()

    def __init__(self, charm: CharmBase, relationship_name: str, auth_type: str, **kwargs):
        super().__init__(charm, relationship_name)
        self._charm = charm
        self._relationship_name = relationship_name
        self._auth_conf = self._build_conf_dict(auth_type, **kwargs)
        self.framework.observe(
            charm.on[relationship_name].relation_joined, self._set_auth_config_in_relation_data
        )
        self.framework.observe(
            charm.on[relationship_name].relation_changed, self._on_auth_relation_changed
        )

    def _build_conf_dict(self, auth_type, **kwargs) -> dict:
        """Builds a dictionary for authentication configuration that matches the json schema of the provider.
        Args:
            auth_type (str): authentication type to be set in the configuration dict.
            kwargs: key and value pairs provided to configure authentication mode.
        Returns:
            dict: Authentication configuration as a dictionary.
        """
        return {auth_type: { key:value for key, value in kwargs.items()}}

    def _set_auth_config_in_relation_data(self, event: RelationJoinedEvent) -> None:
        """Handler triggered on relation joined event. Adds authentication config to relation data.
        Args:
            event: Juju event
        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return
        relation_data = event.relation.data[self.model.app]
        relation_data["auth"] = json.dumps(self._auth_conf)

    def _on_auth_relation_changed(self,event: RelationChangedEvent) -> None:
        """Handler triggered on relation changed events. 
        Extracts grafana url from relation data and emits the url_available event
        Args:
            event: Juju event
        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return

        url_json = event.relation.data[event.app].get("url", "")
        if not url_json:
            logger.warning("No url found in relation data")
            return

        url = json.loads(url_json)

        try:
            validate({"application-data":{"url":url}}, REQUIRER_JSON_SCHEMA)
        except:
            logger.warning("Relation data did not pass JSON Schema validation")
            return

        self.on.url_available.emit(
            url=url,
            relation_id=event.relation.id,
        )


class AuthConfAvailableEvent(EventBase):
    """Charm Event triggered when authentication config is ready."""

    def __init__(self, handle, auth: dict, relation_id: int):
        super().__init__(handle)
        self.auth = auth
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "auth": self.auth,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.auth = snapshot["auth"]
        self.relation_id = snapshot["relation_id"]


class AuthRequirerCharmEvents(CharmEvents):
    """List of events that the grafana auth requirer charm can leverage."""

    auth_conf_available = EventSource(AuthConfAvailableEvent)


class GrafanaAuthRequires(Object):
    """Grafana authentication configuration requirer class to be initialized by grafana-auth requirers"""

    on = AuthRequirerCharmEvents()

    def __init__(self, charm, relationship_name: str, url: str):
        super().__init__(charm, relationship_name)
        self._charm = charm
        self._relationship_name = relationship_name
        self._url = url
        self.framework.observe(
            charm.on[relationship_name].relation_changed, self._on_auth_relation_changed
        )
        self.framework.observe(
            charm.on[relationship_name].relation_joined, self._set_url_in_relation_data
        )

    def _on_auth_relation_changed(self, event) -> None:
        """Handler triggered on relation changed events.
        Args:
            event: Juju event
        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return

        auth_conf_json = event.relation.data[event.app].get("auth", "")

        if not auth_conf_json:
            logger.warning("No authentication config found in relation data")
            return

        auth_conf = json.loads(auth_conf_json)

        try:
            validate({"application-data":{"auth":auth_conf}}, PROVIDER_JSON_SCHEMA)
        except:
            logger.warning("Relation data did not pass JSON Schema validation")
            return

        self.on.auth_conf_available.emit(
            auth=auth_conf,
            relation_id=event.relation.id,
        )

    def _set_url_in_relation_data(self, event: RelationJoinedEvent) -> None:
        """Handler triggered on relation joined events. Adds URL to relation data.
        Args:
            event: Juju event
        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return
        relation_data = event.relation.data[self.model.app]
        relation_data["url"] = json.dumps(self._url)
