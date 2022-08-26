#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""A charm to functionally test the auth provider in gafana-auth library."""

import logging

from charms.grafana_auth_interface.v0.grafana_auth_interface import (
    GrafanaAuthProxyProvider,
)
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, WaitingStatus

logger = logging.getLogger(__name__)


class AuthProviderTesterCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.container = self.unit.get_container("auth-provider-tester")
        self.grafana_auth_proxy_provider = GrafanaAuthProxyProvider(self)
        self.framework.observe(
            self.grafana_auth_proxy_provider.on.urls_available, self._on_urls_available
        )

    def _on_urls_available(self, event):
        if not event.urls:
            self.unit.status = WaitingStatus("Waiting for grafana urls")
            event.defer()
            return
        self.urls = event.urls
        logger.info("urls have been set: {}".format(self.urls))
        self.unit.status = ActiveStatus()


if __name__ == "__main__":
    main(AuthProviderTesterCharm)
