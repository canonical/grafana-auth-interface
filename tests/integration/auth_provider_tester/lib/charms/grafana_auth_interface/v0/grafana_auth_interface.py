# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""grafana-auth interface library.

This library implements the grafana-auth relation interface,
it contains the Requirer and Provider classes for handling
the interface.
This library is designed to allow charms to configure authentication to Grafana,
the provider will set the authentication mode that it needs,
and will pass the necessary configuration of that authentication mode.
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
An example on how to use the AuthProvider with proxy mode using default configuration options.
The default arguments are:
    `charm : CharmBase`
    `relationship_name: str : grafana-auth`
    `header_name: str : X-WEBAUTH-USER`
    `header_property: str : username`
    `auto_sign_up: bool : True`
    `sync_ttl: int : None`
    `whitelist: list[str] : None`
    `headers: list[str] : None`
    `headers_encoded: bool : None`
    `enable_login_token: bool : None`
```python
from charms.grafana_auth_interface.v0.grafana_auth_interface import GrafanaAuthProxyProvider
from ops.charm import CharmBase
class ExampleProviderCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        ...
        self.grafana_auth_proxy_provider = GrafanaAuthProxyProvider(self)
        self.framework.observe(
            self.grafana_auth_proxy_provider.on.urls_available, self._on_urls_available
        )
        ...
```
Values different than defaults must be set from the class constructor.
The [official documentation](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/auth-proxy/)
of Grafana provides further explanation on the values that can be assigned to the different variables.
Example:
```python
from charms.grafana_auth_interface.v0.grafana_auth_interface import GrafanaAuthProxyProvider
from ops.charm import CharmBase
class ExampleProviderCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        ...
        self.grafana_auth_proxy_provider = GrafanaAuthProxyProvider(
            self,
            header_property="email",
            auto_sign_up=False,
            whitelist=["localhost","canonical.com"],
        )
        self.framework.observe(
            self.grafana_auth_proxy_provider.on.urls_available, self._on_urls_available
        )
        ...
```
### Requirer charm
Example:
An example on how to use the auth requirer.
```python
from charms.grafana_auth_interface.v0.grafana_auth_interface import AuthRequirer
from ops.charm import CharmBase
class ExampleRequirerCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.grafana_auth_requirer = AuthRequirer(
            self,
            grafana_auth_requirer=["https://grafana.example.com/"]
        )
        self.framework.observe(
            self.grafana_auth_requirer.on.auth_config_available, self._on_auth_config_available
        )
```
"""  # noqa

import json
import logging
from typing import Any, Dict, List, Union

from jsonschema import validate  # type: ignore[import]
from ops.charm import (
    CharmBase,
    CharmEvents,
    LeaderElectedEvent,
    PebbleReadyEvent,
    RelationChangedEvent,
    RelationJoinedEvent,
)
from ops.framework import EventBase, EventSource, Object, StoredDict, StoredList

# The unique Charmhub library identifier, never change it
LIBID = "bd7d0356fdc74c65bb206be3b843fbfa"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

AUTH_PROXY_PROVIDER_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "$id": "https://canonical.github.io/charm-relation-interfaces/grafana_auth/schemas/provider.json",
    "type": "object",
    "title": "`grafana_auth` provider schema",
    "description": "The `grafana_auth` root schema comprises the entire provider databag for this interface.",
    "documentation": "https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/auth-proxy/",
    "default": {},
    "examples": [
        {
            "application-data": {
                "auth": {
                    "proxy": {
                        "enabled": True,
                        "header_name": "X-WEBAUTH-USER",
                        "header_property": "username",
                        "auto_sign_up": True,
                    }
                }
            }
        }
    ],
    "required": ["application-data"],
    "properties": {
        "application-data": {
            "$id": "#/properties/application-data",
            "title": "Application Databag",
            "type": "object",
            "additionalProperties": True,
            "required": ["auth"],
            "properties": {
                "auth": {
                    "additionalProperties": True,
                    "anyOf": [{"required": ["proxy"]}],
                    "type": "object",
                    "properties": {
                        "proxy": {
                            "$id": "#/properties/application-data/proxy",
                            "type": "object",
                            "required": ["header_name", "header_property"],
                            "additionalProperties": True,
                            "properties": {
                                "enabled": {
                                    "$id": "#/properties/application-data/proxy/enabled",
                                    "type": "boolean",
                                    "default": True,
                                },
                                "header_name": {
                                    "$id": "#/properties/application-data/proxy/header_name",
                                    "type": "string",
                                },
                                "header_property": {
                                    "$id": "#/properties/application-data/proxy/header_property",
                                    "type": "string",
                                },
                                "auto_sign_up": {
                                    "$id": "#/properties/application-data/proxy/auto_sign_up",
                                    "type": "boolean",
                                    "default": True,
                                },
                                "sync_ttl": {
                                    "$id": "#/properties/application-data/proxy/sync_ttl",
                                    "type": "integer",
                                    "default": 60,
                                },
                                "whitelist": {
                                    "$id": "#/properties/application-data/proxy/whitelist",
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "headers": {
                                    "$id": "#/properties/application-data/proxy/headers",
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "headers_encoded": {
                                    "$id": "#/properties/application-data/proxy/headers_encoded",
                                    "type": "boolean",
                                    "default": False,
                                },
                                "enable_login_token": {
                                    "$id": "#/properties/application-data/proxy/enable_login_token",
                                    "type": "boolean",
                                    "default": False,
                                },
                            },
                        }
                    },
                }
            },
        }
    },
    "additionalProperties": True,
}
REQUIRER_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "$id": "https://canonical.github.io/charm-relation-interfaces/interfaces/grafana_auth/schemas/requirer.json",
    "type": "object",
    "title": "`grafana_auth` requirer schema",
    "description": "The `grafana_auth` root schema comprises the entire consumer databag for this interface.",
    "default": {},
    "examples": [{"application-data": {"urls": ["https://grafana.example.com/"]}}],
    "required": ["application-data"],
    "properties": {
        "application-data": {
            "$id": "#/properties/application-data",
            "title": "Application Databag",
            "type": "object",
            "additionalProperties": True,
            "required": ["urls"],
            "urls": {"$id": "#/properties/application-data/urls", "type": "list"},
        }
    },
    "additionalProperties": True,
}

DEFAULT_RELATION_NAME = "grafana-auth"
AUTH = "auth"
logger = logging.getLogger(__name__)


def _type_convert_stored(obj):
    """Convert Stored* to their appropriate types, recursively."""
    if isinstance(obj, StoredList):
        return list(map(_type_convert_stored, obj))
    elif isinstance(obj, StoredDict):
        return {k: _type_convert_stored(obj[k]) for k in obj.keys()}
    else:
        return obj


class UrlsAvailableEvent(EventBase):
    """Charm event triggered when provider charm extracts the urls from relation data."""

    def __init__(self, handle, urls: list, relation_id: int):
        super().__init__(handle)
        self.urls = urls
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "urls": self.urls,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.urls = _type_convert_stored(snapshot["urls"])
        self.relation_id = snapshot["relation_id"]


class AuthProviderCharmEvents(CharmEvents):
    """List of events that the auth provider charm can leverage."""

    urls_available = EventSource(UrlsAvailableEvent)


class AuthProvider(Object):
    """Authentication configuration provider class to be initialized by auth providers."""

    on = AuthProviderCharmEvents()

    def __init__(self, charm: CharmBase, relationship_name: str):
        super().__init__(charm, relationship_name)
        self._auth_config = {}  # type: Dict[str, Dict[str, Any]]
        self._charm = charm
        self._relationship_name = relationship_name
        container = list(self._charm.meta.containers.values())[0]
        if len(self._charm.meta.containers) == 1:
            refresh_event = self._charm.on[container.name.replace("-", "_")].pebble_ready
            self.framework.observe(refresh_event, self._get_urls_from_relation_data)
        self.framework.observe(
            self._charm.on[relationship_name].relation_joined,
            self._set_auth_config_in_relation_data,
        )
        self.framework.observe(
            self._charm.on.leader_elected, self._set_auth_config_in_relation_data
        )
        self.framework.observe(
            self._charm.on[relationship_name].relation_changed, self._get_urls_from_relation_data
        )

    def _set_auth_config_in_relation_data(
        self, event: Union[LeaderElectedEvent, RelationJoinedEvent]
    ) -> None:
        """Handler triggered on relation joined event. Adds authentication config to relation data.
        Args:
            event: Juju event
        Returns:
            None
        """  # noqa
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relationship_name)
        if not relation:
            logger.warning("Relation {} has not been created yet".format(self._relationship_name))
            return

        if not self._auth_config:
            logger.warning(
                "No authentication configuration was given by for application {} , it won't be set in relation {}".format(
                    self.model.app, relation.id
                )
            )
            return
        if not self._validate_auth_config_json_schema():
            logger.warning(
                "Authentication configuration provided by application {} did not pass JSON schema validation, it won't be set in relation {}".format(
                    self.model.app, relation.id
                )
            )
        relation_data = relation.data[self._charm.app]
        relation_data[AUTH] = json.dumps(self._auth_config)

    def _get_urls_from_relation_data(
        self, event: Union[PebbleReadyEvent, RelationChangedEvent]
    ) -> None:
        """Handler triggered on relation changed and pebble_ready events.
        Extracts urls from relation data and emits the urls_available event
        Args:
            event: Juju event
        Returns:
            None
        """  # noqa
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relationship_name)
        if not relation:
            logger.warning("Relation {} has not been created yet".format(self._relationship_name))
            return
        urls_json = relation.data[relation.app].get("urls", "")  # type: ignore
        if not urls_json:
            logger.warning("No urls found in {} relation data".format(self._relationship_name))
            return

        urls = json.loads(urls_json)

        self.on.urls_available.emit(urls=urls, relation_id=relation.id)

    def _validate_auth_config_json_schema(self) -> bool:
        """Validates authentication configuration using json schemas.
        Returns:
            bool: Whether the configuration is valid or not based on the json schema.
        """  # noqa
        return False


class AuthConfAvailableEvent(EventBase):
    """Charm Event triggered when authentication config is ready."""

    def __init__(self, handle, auth: dict, relation_id: int):
        super().__init__(handle)
        self.auth = auth
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            AUTH: self.auth,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.auth = _type_convert_stored(snapshot[AUTH])
        self.relation_id = snapshot["relation_id"]


class AuthRequirerCharmEvents(CharmEvents):
    """List of events that the auth requirer charm can leverage."""

    auth_conf_available = EventSource(AuthConfAvailableEvent)


class AuthRequirer(Object):
    """Authentication configuration requirer class to be initialized by auth requirers."""

    on = AuthRequirerCharmEvents()

    def __init__(
        self,
        charm,
        urls: List[str],
        relationship_name: str = DEFAULT_RELATION_NAME,
    ):
        super().__init__(charm, relationship_name)
        self._charm = charm
        self._relationship_name = relationship_name
        self._urls = urls
        container = list(self._charm.meta.containers.values())[0]
        if len(self._charm.meta.containers) == 1:
            refresh_event = self._charm.on[container.name.replace("-", "_")].pebble_ready
            self.framework.observe(refresh_event, self._get_auth_config_from_relation_data)
        self.framework.observe(
            self._charm.on[relationship_name].relation_changed,
            self._get_auth_config_from_relation_data,
        )
        self.framework.observe(
            self._charm.on[relationship_name].relation_joined, self._set_urls_in_relation_data
        )
        self.framework.observe(self._charm.on.leader_elected, self._set_urls_in_relation_data)

    def _set_urls_in_relation_data(
        self, event: Union[LeaderElectedEvent, RelationJoinedEvent]
    ) -> None:
        """Handler triggered on relation joined events. Adds URL(s) to relation data.
        Args:
            event: Juju event
        Returns:
            None
        """  # noqa
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relationship_name)
        if not relation:
            logger.warning("Relation {} has not been created yet".format(self._relationship_name))
            return

        if not self._urls:
            logger.warning(
                "No urls were given for application {}, urls won't be set in relation {}".format(
                    self.model.app, relation.id
                )
            )
            return
        try:
            validate({"application-data": {"urls": self._urls}}, REQUIRER_JSON_SCHEMA)
        except:  # noqa: E722
            logger.warning(
                "urls provided by application {} did not pass JSON schema validation, urls won't be set in relation {}".format(
                    self.model.app, relation.id
                )
            )
            return
        relation_data = relation.data[self._charm.app]
        relation_data["urls"] = json.dumps(self._urls)

    def _get_auth_config_from_relation_data(
        self, event: Union[PebbleReadyEvent, RelationChangedEvent]
    ) -> None:
        """Handler triggered on relation changed and pebble_ready events.
        Extracts authentication config from relation data and emits an event that contains the config.
        Args:
            event: Juju event
        Returns:
            None
        """  # noqa
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relationship_name)
        if not relation:
            logger.warning("Relation {} has not been created yet".format(self._relationship_name))
            return

        auth_conf_json = relation.data[relation.app].get(AUTH, "")

        if not auth_conf_json:
            logger.warning(
                "No authentication config found in {} relation data".format(
                    self._relationship_name
                )
            )
            return

        auth_conf = json.loads(auth_conf_json)

        self.on.auth_conf_available.emit(
            auth=auth_conf,
            relation_id=relation.id,
        )


class GrafanaAuthProxyProvider(AuthProvider):
    """Provider object for Grafana Auth.
    Uses Proxy as the authentication mode and provider and interface to configure Proxy authentication to Grafana
    """  # noqa

    _AUTH_TYPE = "proxy"
    _ENABLED = True

    def __init__(
        self,
        charm: CharmBase,
        relationship_name: str = DEFAULT_RELATION_NAME,
        header_name: str = "X-WEBAUTH-USER",
        header_property: str = "username",
        auto_sign_up: bool = True,
        sync_ttl: int = None,
        whitelist: List[str] = None,
        headers: List[str] = None,
        headers_encoded: bool = None,
        enable_login_token: bool = None,
    ) -> None:
        """Constructs GrafanaAuthProxyProvider.
        Args:
            charm : CharmBase : the charm which manages this object.
            relationship_name : str : name of the relation that provider the Grafana authentication config.
            header_name : str : HTTP Header name that will contain the username or email
            header_property : str : HTTP Header property, defaults to username but can also be email.
            auto_sign_up : bool : Set to `true` to enable auto sign up of users who do not exist in Grafana DB.
            sync_ttl : int : Define cache time to live in minutes.
            whitelist : list[str] : Limits where auth proxy requests come from by configuring a list of IP addresses.
            headers : list[str]
            headers_encoded : bool
            enable_login_token : bool
        Returns:
            None
        """  # noqa
        super().__init__(charm, relationship_name)
        config_options = {}  # type: Dict[str,Any]
        config_options["enabled"] = self._ENABLED
        config_options["header_name"] = header_name
        config_options["header_property"] = header_property
        config_options["auto_sign_up"] = auto_sign_up
        if sync_ttl is not None:
            config_options["sync_ttl"] = sync_ttl
        if whitelist is not None and whitelist:
            config_options["whitelist"] = whitelist
        if headers is not None and headers:
            config_options["headers"] = headers
        if headers_encoded is not None:
            config_options["headers_encoded"] = headers_encoded
        if enable_login_token is not None:
            config_options["enable_login_token"] = enable_login_token
        self._auth_config = {self._AUTH_TYPE: config_options}

    def _validate_auth_config_json_schema(self) -> bool:
        """Validates authentication configuration using json schemas.
        Returns:
            bool: Whether the configuration is valid or not based on the json schema.
        """  # noqa
        try:
            validate(
                {"application-data": {"auth": self._auth_config}}, AUTH_PROXY_PROVIDER_JSON_SCHEMA
            )
            return True
        except:  # noqa: E722
            return False
