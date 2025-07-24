#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from pathlib import Path

import yaml
from juju.model import Model

CHARM_METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = CHARM_METADATA["name"]
TIMEOUT = 60 * 10
VELERO_CHARM = "velero-operator"


def is_relation_joined(model: Model, endpoint: str) -> bool:
    """Check if a relation is joined.

    Args:
        model: The Juju model to check.
        endpoint: The name of the relation endpoint to check.
    """
    for rel in model.relations:
        endpoints = {endpoint.name for endpoint in rel.endpoints}
        if endpoint in endpoints:
            return True
    return False
