#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

import jubilant
import pytest
from helpers import (
    create_namespace,
    create_pod_reader_cluster_role,
    create_pod_reader_role,
    delete_namespace,
    delete_pod_reader_cluster_role,
    delete_pod_reader_role,
    get_expected_infra_backup_data_bag,
    get_expected_namespaced_infra_backup_data_bag,
    get_velero_spec,
    list_roles_clusterroles,
    wait_for_backup_spec,
)
from pytest_jubilant import pack

from literals import APP_NAME, ROLES_RESOURCE, S3_INTEGRATOR, VELERO_CHARM
from src.literals import CLUSTER_INFRA_BACKUP, NAMESPACED_INFRA_BACKUP

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
    """Build the infra-backup-operator and deploy velero and s3-integrator."""
    charm_root = Path(__file__).resolve().parents[2]
    juju.deploy(pack(charm_root).resolve())
    juju.deploy(VELERO_CHARM, trust=True, channel="edge")
    juju.deploy(S3_INTEGRATOR)
    juju.wait(jubilant.all_blocked, timeout=240)


@pytest.mark.setup
def test_relate(juju: jubilant.Juju) -> None:
    """Set the necessary relations."""
    for relation in [CLUSTER_INFRA_BACKUP, NAMESPACED_INFRA_BACKUP]:
        logger.info("Setting %s relation with Velero", relation)
        juju.integrate(f"{APP_NAME}:{relation}", VELERO_CHARM)

    juju.integrate(S3_INTEGRATOR, VELERO_CHARM)

    juju.wait(lambda status: jubilant.all_active(status, APP_NAME))
    logger.info("Infra Backup Operator ready")


@pytest.mark.setup
def test_configure_s3_integrator(
    juju: jubilant.Juju, s3_cloud_credentials: dict[str, str], s3_cloud_configs: dict[str, str]
) -> None:
    """Configure the integrator charm with credentials and configs for s3 compatible bucket."""
    logger.info("Setting credentials for %s", S3_INTEGRATOR)
    juju.config(S3_INTEGRATOR, s3_cloud_configs)
    s3_unit = list(juju.status().apps[S3_INTEGRATOR].units.keys())[0]
    juju.run(s3_unit, "sync-s3-credentials", s3_cloud_credentials)
    juju.wait(lambda status: jubilant.all_active(status, S3_INTEGRATOR))


def test_infra_backup_relation(juju: jubilant.Juju) -> None:
    """Simulate enabling the load-balancer l2-mode and the creation of the metallb-system ns."""
    create_namespace("metallb-system")
    with fast_forward(juju):
        wait_for_backup_spec(
            lambda: get_velero_spec(juju, CLUSTER_INFRA_BACKUP),
            get_expected_infra_backup_data_bag(["metallb-system"]),
        )


def test_infra_backup_relation_update(juju: jubilant.Juju) -> None:
    """metallb-system ns is not included in the backup if doesn't exist."""
    delete_namespace("metallb-system")
    with fast_forward(juju):
        wait_for_backup_spec(
            lambda: get_velero_spec(juju, CLUSTER_INFRA_BACKUP),
            get_expected_infra_backup_data_bag(),
        )


def test_wrong_config_blocks_charm(juju: jubilant.Juju) -> None:
    """An invalid namespace blocks the charm to warn the user."""
    juju.config(APP_NAME, {"namespaces": ""})
    with fast_forward(juju):
        (lambda status: jubilant.all_blocked(status, APP_NAME),)

    juju.config(APP_NAME, reset="namespaces")
    with fast_forward(juju):
        juju.wait(lambda status: jubilant.all_active(status, APP_NAME))


def test_namespaced_infra_backup_relation(juju: jubilant.Juju) -> None:
    """Test if the namespaced-infra-backup has the expected content."""
    wait_for_backup_spec(
        lambda: get_velero_spec(juju, NAMESPACED_INFRA_BACKUP),
        get_expected_namespaced_infra_backup_data_bag(),
    )


def test_create_backup(juju: jubilant.Juju) -> None:
    """Test create-backup action of the velero-operator charm."""
    # role makes part of the namespace-infra-backup
    create_pod_reader_role()
    # cluster role makes part of the cluster-infra-backup
    create_pod_reader_cluster_role()

    velero_unit = list(juju.status().apps[VELERO_CHARM].units.keys())[0]

    logger.info("Running the create-backup action for cluster-infra-backup")
    task_cluster = juju.run(
        velero_unit, "create-backup", {"target": f"{APP_NAME}:{CLUSTER_INFRA_BACKUP}"}
    )
    assert task_cluster.results["status"] == "success"

    logger.info("Running the create-backup action for cluster-infra-backup")
    task_namespaced = juju.run(
        velero_unit, "create-backup", {"target": f"{APP_NAME}:{NAMESPACED_INFRA_BACKUP}"}
    )
    assert task_namespaced.results["status"] == "success"


def test_restore(juju: jubilant.Juju) -> None:
    """Simulate a disaster by removing resources and then restore and ensure that is back."""
    delete_pod_reader_role()
    delete_pod_reader_cluster_role()
    before_backup_roles_clusterroles = list_roles_clusterroles()
    assert ROLES_RESOURCE not in before_backup_roles_clusterroles["roles"]
    assert ROLES_RESOURCE not in before_backup_roles_clusterroles["cluster_roles"]

    velero_unit = list(juju.status().apps[VELERO_CHARM].units.keys())[0]
    task = juju.run(velero_unit, "list-backups")
    backups = task.results["backups"]
    backup_uids = [
        uid
        for uid, _ in sorted(
            backups.items(),
            key=lambda item: datetime.strptime(item[1]["start-timestamp"], "%Y-%m-%dT%H:%M:%SZ"),
        )
    ]

    logger.info("Creating restores for each backup")
    for backup_uid in backup_uids:
        juju.run(velero_unit, "restore", {"backup-uid": backup_uid})

    logger.info("Verifying the restore")
    after_backup_roles_clusterroles = list_roles_clusterroles()
    assert ROLES_RESOURCE in after_backup_roles_clusterroles["roles"]
    assert ROLES_RESOURCE in after_backup_roles_clusterroles["cluster_roles"]
