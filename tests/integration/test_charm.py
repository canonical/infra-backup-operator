#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import logging

import pytest
from helpers import APP_NAME, TIMEOUT, VELERO_CHARM, is_relation_joined
from pytest_operator.plugin import OpsTest

from charm import CLUSTER_INFRA_BACKUP

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build and deploy the infra-backup-operator."""
    logger.info("Building infra-backup-operator charm")
    charm = await ops_test.build_charm(".")

    app = await ops_test.model.deploy(charm)
    await ops_test.model.deploy(VELERO_CHARM, trust=True, channel="edge")

    await ops_test.model.wait_for_idle(apps=[APP_NAME, VELERO_CHARM], status="blocked", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_relate_and_trust(ops_test: OpsTest):
    logger.info("Relating velero-operator to %s", APP_NAME)
    model = ops_test.model

    await ops_test.juju("trust", APP_NAME, "--scope=cluster")

    await model.integrate(
        f"{APP_NAME}:{CLUSTER_INFRA_BACKUP}",
        f"{VELERO_CHARM}:",
    )

    async with ops_test.fast_forward(fast_interval="30s"):
        await model.block_until(lambda: is_relation_joined(model, CLUSTER_INFRA_BACKUP))
        await model.wait_for_idle(
            apps=[APP_NAME],
            status="active",
            timeout=TIMEOUT,
        )
