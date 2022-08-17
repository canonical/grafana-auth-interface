#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from unittest.mock import Mock, PropertyMock, call, patch

from charms.grafana_auth_interface.v0.grafana_auth_interface import (
    GrafanaAuthProvides,
    GrafanaAuthRequires,
)

PROVIDER_UNIT_NAME = "leader unit provider"
REQUIRER_UNIT_NAME = "leader unit requirer"
PROVIDER_APP_NAME = "provider app"
REQUIRER_APP_NAME = "requirer app"
CHARM_LIB_PATH = "charms.grafana_auth_interface.v0.grafana_auth_interface"
AUTH_TYPE = "proxy"
HEADER_NAME = "X-WEBAUTH-USER"
HEADER_PROPERTY = "username"
AUTO_SIGN_UP = False
RELATIONSHIP_NAME = "grafana_auth"
EXAMPLE_URL = "https://example.com/"


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


class TestGrafanaAuthProvides(unittest.TestCase):
    def setUp(self):
        class MockRelation:
            def relation_changed(self):
                pass

            def relation_joined(self):
                pass

        charm = Mock()
        charm.on = {RELATIONSHIP_NAME: MockRelation()}
        self.charm = charm
        self.provider_unit = UnitMock(name=PROVIDER_UNIT_NAME)
        self.provider_app = AppMock(name=PROVIDER_APP_NAME)
        self.requirer_app = AppMock(name=REQUIRER_APP_NAME)
        self.charm.unit = self.provider_unit
        self.grafana_auth_provides = GrafanaAuthProvides(
            charm=charm,
            relationship_name=RELATIONSHIP_NAME,
            auth_type=AUTH_TYPE,
            header_name=HEADER_NAME,
            header_property=HEADER_PROPERTY,
            auto_sign_up=False,
        )
        self.charm.framework.model.app = self.provider_app

    def test_given_auth_mode_config_and_unit_is_leader_when_relation_joined_then_auth_conf_is_set_in_relation_databag(
        self,
    ):
        self.provider_unit.set_leader(True)
        expected_conf_dict = {
            AUTH_TYPE: {
                "header_property": HEADER_PROPERTY,
                "header_name": HEADER_NAME,
                "auto_sign_up": AUTO_SIGN_UP,
            }
        }
        event = Mock()
        event.relation.id = 1
        event.relation.data = {
            self.provider_app: {},
        }
        self.grafana_auth_provides._set_auth_config_in_relation_data(event)
        actual_conf_dict = json.loads(event.relation.data[self.provider_app].get("auth"))
        self.assertDictEqual(expected_conf_dict, actual_conf_dict)

    def test_given_auth_mode_config_and_unit_is_not_leader_when_relation_joined_then_auth_conf_is_not_set_in_relation_databag(
        self,
    ):
        self.provider_unit.set_leader(False)
        event = Mock()
        event.relation.data = {
            self.provider_app: json.dumps({}),
        }
        self.grafana_auth_provides._set_auth_config_in_relation_data(event)
        relation_data = json.loads(event.relation.data[self.provider_app])
        self.assertNotIn("auth", relation_data)

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.url_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_url_in_databag_and_unit_is_leader_when_on_grafana_auth_relation_changed_then_grafana_url_available_event_is_emitted(
        self, patch_emit
    ):
        self.provider_unit.set_leader(True)
        event = Mock()
        event.relation.data = {
            self.requirer_app: {"url": json.dumps(EXAMPLE_URL)},
        }
        event.app = self.requirer_app
        relation_id = 1
        event.relation.id = relation_id
        self.grafana_auth_provides._on_auth_relation_changed(event)
        calls = [
            call().emit(
                url=EXAMPLE_URL,
                relation_id=relation_id,
            ),
        ]
        patch_emit.assert_has_calls(calls, any_order=True)

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.url_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_url_not_in_databag_and_unit_is_not_leader_when_on_grafana_auth_relation_changed_then_grafana_url_available_event_is_not_emitted(
        self, patch_emit
    ):
        self.provider_unit.set_leader(False)
        event = Mock()
        self.grafana_auth_provides._on_auth_relation_changed(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.url_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_grafana_url_in_relation_databag_when_schema_is_not_valid_then_grafana_url_available_event_is_not_emitted(
        self, patch_emit
    ):
        event = Mock()
        event.relation.data = {
            self.requirer_app: {"wrong_key": json.dumps(EXAMPLE_URL)},
        }
        event.app = self.requirer_app
        self.grafana_auth_provides._on_auth_relation_changed(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.url_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_url_not_in_databag_and_unit_is_leader_when_on_grafana_auth_relation_changed_then_grafana_url_available_event_is_not_emitted(
        self, patch_emit
    ):
        self.provider_unit.set_leader(True)
        event = Mock()
        event.relation.data = {
            self.requirer_app: {"not_url": ""},
        }
        event.app = self.requirer_app
        self.grafana_auth_provides._on_auth_relation_changed(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.url_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_grafana_url_in_relation_databag_when_unit_is_not_leader_then_grafana_url_available_event_is_not_emitted(
        self, patch_emit
    ):
        self.provider_unit.set_leader(False)
        event = Mock()
        event.relation.data = {
            self.requirer_app: {"url": EXAMPLE_URL},
        }
        event.app = self.requirer_app
        self.grafana_auth_provides._on_auth_relation_changed(event)
        patch_emit.assert_not_called()


class TestGrafanaAuthRequires(unittest.TestCase):
    def setUp(self):
        class MockRelation:
            def relation_joined(self):
                pass

            def relation_changed(self):
                pass

        self.requirer_unit = UnitMock(name=REQUIRER_UNIT_NAME)
        self.provider_app = AppMock(name=PROVIDER_APP_NAME)
        self.requirer_app = AppMock(name=REQUIRER_APP_NAME)
        self.charm = Mock()
        self.charm.on = {RELATIONSHIP_NAME: MockRelation()}
        self.charm.unit = self.requirer_unit
        self.grafana_auth_requires = GrafanaAuthRequires(
            self.charm, relationship_name=RELATIONSHIP_NAME, url=EXAMPLE_URL
        )
        self.charm.framework.model.app = self.requirer_app

    def test_given_unit_is_leader_when_relation_joined_then_grafana_url_is_set_in_relation_databag(
        self,
    ):
        self.requirer_unit.set_leader(True)
        event = Mock()
        event.relation.id = 1
        event.relation.data = {
            self.requirer_app: {},
        }
        self.grafana_auth_requires._set_url_in_relation_data(event)
        actual_grafana_url = json.loads(event.relation.data[self.requirer_app].get("url"))
        self.assertEqual(EXAMPLE_URL, actual_grafana_url)

    def test_given_unit_is_not_leader_when_relation_joined_then_grafana_url_is_not_set_in_relation_databag(
        self,
    ):
        self.requirer_unit.set_leader(False)
        event = Mock()
        event.relation.id = 1
        event.relation.data = {
            self.requirer_app: json.dumps({}),
        }
        self.grafana_auth_requires._set_url_in_relation_data(event)
        relation_data = json.loads(event.relation.data[self.requirer_app])
        self.assertNotIn("url", relation_data)

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_auth_conf_in_relation_databag_and_unit_is_leader_when_grafana_auth_relation_changed_then_grafana_auth_config_available_event_is_emitted(
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
        event.relation.data = {
            self.provider_app: {"auth": json.dumps(conf_dict)},
        }
        event.app = self.provider_app
        relation_id = 1
        event.relation.id = relation_id
        self.grafana_auth_requires._on_auth_relation_changed(event)
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
    def test_given_grafana_auth_conf_in_relation_databag_and_unit_is_not_leader_when_grafana_auth_relation_changed_then_grafana_auth_config_available_event_not_is_emitted(
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
        self.grafana_auth_requires._on_auth_relation_changed(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_auth_conf_in_relation_databag_and_auth_mode_not_valid_when_grafana_auth_relation_changed_then_grafana_auth_config_available_event_is_not_emitted(
        self, patch_emit
    ):
        event = Mock()
        wrong_conf_dict = {
            "wrong auth mode": {
                "header_property": HEADER_PROPERTY,
                "header_name": HEADER_NAME,
                "auto_sign_up": AUTO_SIGN_UP,
            }
        }
        event.relation.data = {
            self.provider_app: {"auth": json.dumps(wrong_conf_dict)},
        }
        event.app = self.provider_app
        self.grafana_auth_requires._on_auth_relation_changed(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_auth_conf_in_relation_databag_and_schema_is_not_valid_when_grafana_auth_relation_changed_then_grafana_auth_config_available_event_is_not_emitted(
        self, patch_emit
    ):
        event = Mock()
        wrong_conf_dict = {
            "proxy": {
                "auto_sign_up": AUTO_SIGN_UP,
            }
        }
        event.relation.data = {
            self.provider_app: {"auth": json.dumps(wrong_conf_dict)},
        }
        event.app = self.provider_app
        self.grafana_auth_requires._on_auth_relation_changed(event)
        patch_emit.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_grafana_auth_conf_not_in_relation_databag_and_unit_is_leader_when_grafana_auth_relation_changed_then_grafana_auth_config_available_event_is_not_emitted(
        self, patch_emit
    ):
        self.requirer_unit.set_leader(True)
        event = Mock()
        event.relation.data = {
            self.provider_app: {"not_auth_conf": ""},
        }
        event.app = self.provider_app
        self.grafana_auth_requires._on_auth_relation_changed(event)
        patch_emit.assert_not_called()
