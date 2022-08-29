#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from unittest.mock import Mock, PropertyMock, call, patch

from lib.charms.grafana_auth_interface.v0.grafana_auth_interface import (
    AuthRequirer,
    GrafanaAuthProxyProvider,
)

PROVIDER_UNIT_NAME = "leader unit provider"
REQUIRER_UNIT_NAME = "leader unit requirer"
PROVIDER_APP_NAME = "provider app"
REQUIRER_APP_NAME = "requirer app"
CHARM_LIB_PATH = "lib.charms.grafana_auth_interface.v0.grafana_auth_interface"
AUTH_TYPE = "proxy"
HEADER_NAME = "X-WEBAUTH-USER"
HEADER_PROPERTY = "username"
AUTO_SIGN_UP = True
RELATIONSHIP_NAME = "grafana-auth"
EXAMPLE_URLS = ["https://example.com/"]
EXAMPLE_CONTAINER_NAME = "example"
ENABLED = True


class AppMock:
    def __init__(self, name):
        self.name = name


class UnitMock:
    def __init__(self, name, is_leader=True):
        self.name = name
        self.__leader = is_leader

    def is_leader(self):
        return self.__leader

    def set_leader(self, is_leader: bool):
        self.__leader = is_leader


class MockContainerMeta:
    @property
    def name(self):
        return EXAMPLE_CONTAINER_NAME


class MockRelation:
    def relation_changed(self):
        pass

    def relation_joined(self):
        pass

    def pebble_ready(self):
        pass


class MockOn(dict):
    @property
    def leader_elected(self):
        pass


class TestAuthProvider(unittest.TestCase):
    def setUp(self):
        self.charm = Mock()
        self.charm.meta.containers = {"containers": MockContainerMeta()}
        self.charm.on = MockOn(
            {RELATIONSHIP_NAME: MockRelation(), EXAMPLE_CONTAINER_NAME: MockRelation()}
        )
        self.provider_unit = UnitMock(name=PROVIDER_UNIT_NAME)
        self.provider_app = AppMock(name=PROVIDER_APP_NAME)
        self.requirer_app = AppMock(name=REQUIRER_APP_NAME)
        self.charm.unit = self.provider_unit
        self.charm.app = self.provider_app
        self.charm.model = Mock()
        self.grafana_auth_provider = GrafanaAuthProxyProvider(
            charm=self.charm,
        )
        self.charm.framework.model.app = self.provider_app
        self.model = Mock()
        self.model.app = self.provider_app

    def test_given_auth_mode_config_and_unit_is_leader_when_auth_relation_joined_then_auth_conf_is_set_in_relation_databag(
        self,
    ):
        self.provider_unit.set_leader(True)
        expected_conf_dict = {
            AUTH_TYPE: {
                "enabled": ENABLED,
                "header_property": HEADER_PROPERTY,
                "header_name": HEADER_NAME,
                "auto_sign_up": AUTO_SIGN_UP,
            }
        }
        event = Mock()
        relation = Mock()
        relation.data = {
            self.provider_app: {},
        }
        relation.id = 1
        self.charm.model.get_relation.return_value = relation
        self.grafana_auth_provider._set_auth_config_in_relation_data(event)
        actual_conf_dict = json.loads(relation.data[self.provider_app].get("auth"))
        self.assertDictEqual(expected_conf_dict, actual_conf_dict)

    def test_given_auth_mode_config_and_unit_is_not_leader_when_auth_relation_joined_then_auth_conf_is_not_set_in_relation_databag(
        self,
    ):
        self.provider_unit.set_leader(False)
        event = Mock()
        event.relation.data = {
            self.provider_app: json.dumps({}),
        }
        self.grafana_auth_provider._set_auth_config_in_relation_data(event)
        relation_data = json.loads(event.relation.data[self.provider_app])
        self.assertNotIn("auth", relation_data)

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_urls_in_databag_and_unit_is_leader_when_on_auth_relation_changed_then_urls_available_event_is_emitted(
        self, patch_emit
    ):
        self.provider_unit.set_leader(True)
        event = Mock()
        relation_id = 1
        relation = Mock()
        relation.data = {
            self.requirer_app: {"urls": json.dumps(EXAMPLE_URLS)},
        }
        relation.id = relation_id
        relation.app = self.requirer_app
        self.charm.model.get_relation.return_value = relation
        self.grafana_auth_provider._get_urls_from_relation_data(event)
        calls = [
            call().emit(
                urls=EXAMPLE_URLS,
                relation_id=relation_id,
            ),
        ]
        patch_emit.assert_has_calls(calls, any_order=True)

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_urls_not_in_databag_and_unit_is_not_leader_when_on_auth_relation_changed_then_urls_available_event_is_not_emitted(
        self, patch_emit
    ):
        self.provider_unit.set_leader(False)
        event = Mock()
        self.grafana_auth_provider._get_urls_from_relation_data(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_urls_not_in_databag_and_unit_is_leader_when_auth_relation_changed_then_urls_available_event_is_not_emitted(
        self, patch_emit
    ):
        self.provider_unit.set_leader(True)
        event = Mock()
        relation = Mock()
        relation.data = {
            self.requirer_app: {"not_url": ""},
        }
        relation.id = 1
        relation.app = self.requirer_app
        self.charm.model.get_relation.return_value = relation
        self.grafana_auth_provider._get_urls_from_relation_data(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_urls_in_relation_databag_when_unit_is_not_leader_then_urls_available_event_is_not_emitted(
        self, patch_emit
    ):
        self.provider_unit.set_leader(False)
        event = Mock()
        event.relation.data = {
            self.requirer_app: {"urls": EXAMPLE_URLS},
        }
        self.grafana_auth_provider._get_urls_from_relation_data(event)
        patch_emit.assert_not_called()


class TestAuthRequires(unittest.TestCase):
    def setUp(self):
        self.requirer_unit = UnitMock(name=REQUIRER_UNIT_NAME)
        self.provider_app = AppMock(name=PROVIDER_APP_NAME)
        self.requirer_app = AppMock(name=REQUIRER_APP_NAME)
        self.charm = Mock()
        self.charm.meta.containers = {"containers": MockContainerMeta()}
        self.charm.on = MockOn(
            {RELATIONSHIP_NAME: MockRelation(), EXAMPLE_CONTAINER_NAME: MockRelation()}
        )
        self.charm.unit = self.requirer_unit
        self.charm.app = self.requirer_app
        self.charm.model = Mock()
        self.auth_requirer = AuthRequirer(
            self.charm, relationship_name=RELATIONSHIP_NAME, urls=EXAMPLE_URLS
        )
        self.charm.framework.model.app = self.requirer_app

    def test_given_unit_is_leader_when_auth_relation_joined_then_urls_are_set_in_auth_relation_databag(
        self,
    ):
        self.requirer_unit.set_leader(True)
        event = Mock()
        relation = Mock()
        relation.data = {
            self.requirer_app: {},
        }
        relation.id = 1
        self.charm.model.get_relation.return_value = relation
        self.auth_requirer._set_urls_in_relation_data(event)
        actual_urls = json.loads(relation.data[self.requirer_app].get("urls"))
        self.assertEqual(EXAMPLE_URLS, actual_urls)

    def test_given_unit_is_not_leader_when_auth_relation_joined_then_urls_are_not_set_in_auth_relation_databag(
        self,
    ):
        self.requirer_unit.set_leader(False)
        event = Mock()
        event.relation.id = 1
        event.relation.data = {
            self.requirer_app: json.dumps({}),
        }
        self.auth_requirer._set_urls_in_relation_data(event)
        relation_data = json.loads(event.relation.data[self.requirer_app])
        self.assertNotIn("urls", relation_data)

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_auth_conf_in_relation_databag_and_unit_is_leader_when_auth_relation_changed_then_auth_config_available_event_is_emitted(
        self, patch_emit
    ):
        self.requirer_unit.set_leader(True)
        event = Mock()
        conf_dict = {
            AUTH_TYPE: {
                "header_property": HEADER_PROPERTY,
                "header_name": HEADER_NAME,
                "auto_sign_up": AUTO_SIGN_UP,
            }
        }
        relation_id = 1
        relation = Mock()
        relation.data = {
            self.provider_app: {"auth": json.dumps(conf_dict)},
        }
        relation.id = relation_id
        relation.app = self.provider_app
        self.charm.model.get_relation.return_value = relation
        self.auth_requirer._get_auth_config_from_relation_data(event)
        calls = [
            call().emit(
                auth=conf_dict,
                relation_id=relation_id,
            )
        ]
        patch_emit.assert_has_calls(calls, any_order=True)

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_auth_conf_in_relation_databag_and_unit_is_not_leader_when_auth_relation_changed_then_auth_config_available_event_not_is_emitted(
        self, patch_emit
    ):
        self.requirer_unit.set_leader(False)
        event = Mock()
        conf_dict = {
            AUTH_TYPE: {
                "header_property": HEADER_PROPERTY,
                "header_name": HEADER_NAME,
                "auto_sign_up": AUTO_SIGN_UP,
            }
        }
        event.relation.data = {
            self.provider_app: {"auth": json.dumps(conf_dict)},
        }
        event.app = self.provider_app
        self.auth_requirer._get_auth_config_from_relation_data(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_auth_conf_not_in_relation_databag_and_unit_is_leader_when_auth_relation_changed_then_auth_config_available_event_is_not_emitted(
        self, patch_emit
    ):
        self.requirer_unit.set_leader(True)
        event = Mock()
        relation_id = 1
        relation = Mock()
        relation.data = {
            self.provider_app: {"not_auth_conf": ""},
        }
        relation.id = relation_id
        relation.app = self.provider_app
        self.charm.model.get_relation.return_value = relation
        self.auth_requirer._get_auth_config_from_relation_data(event)
        patch_emit.assert_not_called()
