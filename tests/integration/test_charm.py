#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import logging
from pathlib import Path

import jubilant
import pytest
import yaml
from helpers import (
    APP_NAME,
    EXPECTED_CLUSTER_INFRA_BACKUP_DATA_BAG,
    VELERO_CHARM,
    get_app_data_bag,
)
from pytest_jubilant import pack

from charm import CLUSTER_INFRA_BACKUP

logger = logging.getLogger(__name__)


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
def test_check_relation_data(juju: jubilant.Juju) -> None:
    velero_unit = list(juju.status().apps[VELERO_CHARM].units.keys())[0]
    data = yaml.safe_load(juju.cli("show-unit", velero_unit))
    app_data_bag = get_app_data_bag(velero_unit, data)
    spec = json.loads(app_data_bag["spec"])
    assert spec == EXPECTED_CLUSTER_INFRA_BACKUP_DATA_BAG
