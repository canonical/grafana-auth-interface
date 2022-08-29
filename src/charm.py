#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Contains a placeholder dummy charm."""

from ops.charm import CharmBase


class DummyCharm(CharmBase):
    """Placeholder dummy charm."""

    def __init__(self, *args):
        super().__init__(*args)
