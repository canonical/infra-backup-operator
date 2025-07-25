#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from pathlib import Path

import yaml

CHARM_METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = CHARM_METADATA["name"]
VELERO_CHARM = "velero-operator"
VELERO_ENDPOINT = "velero-backups"

EXPECTED_CLUSTER_INFRA_BACKUP_DATA_BAG = {
    "include_namespaces": ["kube-public""kube-system"],
    "include_resources": None,
    "exclude_namespaces": None,
    "exclude_resources": None,
    "label_selector": None,
    "ttl": None,
    "include_cluster_resources": True,
}


def get_app_data_bag(unit: str, data: dict) -> list[dict]:
    """Get the application data bag of Velero Operator where it will configure the backup."""
    relation_data = [v for v in data[unit]["relation-info"] if v["endpoint"] == VELERO_ENDPOINT]
    if len(relation_data) == 0:
        raise ValueError(f"No data found for relation {VELERO_ENDPOINT}")
    return relation_data[0]["application-data"]
