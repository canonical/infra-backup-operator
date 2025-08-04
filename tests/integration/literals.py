# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""literal definitions for integration test."""

from pathlib import Path

import yaml

CHARM_METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = CHARM_METADATA["name"]
VELERO_CHARM = "velero-operator"
VELERO_ENDPOINT = "velero-backups"
