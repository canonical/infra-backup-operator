#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import jubilant
import pytest
from helpers import (
    APP_NAME,
    VELERO_CHARM,
    create_namespace,
    delete_namespace,
    get_expected_infra_backup_data_bag,
    get_velero_spec,
    wait_for_backup_spec,
)
from pytest_jubilant import pack

from charm import CLUSTER_INFRA_BACKUP

logger = logging.getLogger(__name__)


@contextmanager
def fast_forward(juju: jubilant.Juju) -> Iterator[None]:
    """Context manager that temporarily speeds up update-status hooks to fire every 10s."""
    old = juju.model_config()["update-status-hook-interval"]
    juju.model_config({"update-status-hook-interval": "10s"})
    try:
        yield
    finally:
        juju.model_config({"update-status-hook-interval": old})


@pytest.mark.setup
def test_build_deploy_charm(juju: jubilant.Juju) -> None:
    charm_root = Path(__file__).resolve().parents[2]
    juju.deploy(pack(charm_root).resolve())
    juju.deploy(VELERO_CHARM, trust=True, channel="edge")
    juju.wait(jubilant.all_blocked)


@pytest.mark.setup
def test_relate_and_trust(juju: jubilant.Juju) -> None:
    logger.info("Setting trust to infra-backup")
    juju.cli("trust", APP_NAME, "--scope=cluster")
    logger.info("Setting cluster-infra-backup relation with Velero")
    juju.integrate(f"{APP_NAME}:{CLUSTER_INFRA_BACKUP}", f"{VELERO_CHARM}")
    juju.wait(lambda status: jubilant.all_active(status, APP_NAME))
    logger.info("Infra Backup Operator ready")


@pytest.mark.setup
def test_infra_backup_relation(juju: jubilant.Juju) -> None:
    """Simulate enabling the load-balancer l2-mode and the creation of the metallb-system ns."""
    create_namespace("metallb-system")
    with fast_forward(juju):
        wait_for_backup_spec(
            lambda: get_velero_spec(juju), get_expected_infra_backup_data_bag(["metallb-system"])
        )


@pytest.mark.setup
def test_infra_backup_relation_update(juju: jubilant.Juju) -> None:
    """metallb-system ns is not included in the backup if doesn't exist."""
    delete_namespace("metallb-system")
    with fast_forward(juju):
        wait_for_backup_spec(lambda: get_velero_spec(juju), get_expected_infra_backup_data_bag())
