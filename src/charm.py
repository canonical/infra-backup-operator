#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""The Infra Backup Charm."""

import logging

import ops

logger = logging.getLogger(__name__)


class InfraBackupOperatorCharm(ops.CharmBase):
    """A charm for managing a K8s cluster infrastructure backup."""

    def __init__(self, framework: ops.Framework) -> None:
        """Initialise the Infra Backup charm."""
        super().__init__(framework)


if __name__ == "__main__":  # pragma: nocover
    ops.main(InfraBackupOperatorCharm)
