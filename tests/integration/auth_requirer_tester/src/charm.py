#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""A charm to functionally test the auth provider in gafana-auth library."""

import logging

from charms.grafana_auth_interface.v0.grafana_auth_interface import AuthRequirer
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, WaitingStatus

logger = logging.getLogger(__name__)


class AuthRequirerTesterCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.container = self.unit.get_container("auth-requirer-tester")
        self.grafana_auth_proxy_provider = AuthRequirer(self, urls=["https://wwww.example.com"])
        self.framework.observe(
            self.grafana_auth_proxy_provider.on.auth_config_available,
            self._on_auth_config_available,
        )

    def _on_auth_config_available(self, event):
        if not event.auth:
            self.unit.status = WaitingStatus("Waiting for authentication configuration")
            event.defer()
            return
        self.auth = event.auth
        logger.info("auth config has been set: {}".format(self.auth))
        self.unit.status = ActiveStatus()


if __name__ == "__main__":
    main(AuthRequirerTesterCharm)
