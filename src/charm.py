#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""The Infra Backup Charm."""

import logging

import ops
from charms.velero_libs.v0.velero_backup_config import VeleroBackupRequirer, VeleroBackupSpec

from k8s_utils import K8sUtils

logger = logging.getLogger(__name__)

INFRA_NAMESPACES = {"kube-system", "kube-public", "metallb-system"}
CLUSTER_INFRA_BACKUP = "cluster-infra-backup"


class InfraBackupOperatorCharm(ops.CharmBase):
    """A charm for managing a K8s cluster infrastructure backup."""

    def __init__(self, framework: ops.Framework) -> None:
        """Initialise the Infra Backup charm."""
        super().__init__(framework)
        self.k8s_utils = K8sUtils()

        self.framework.observe(self.on.install, self._on_update_status)
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(self.on.upgrade_charm, self._on_update_status)
        self.framework.observe(
            self.on[CLUSTER_INFRA_BACKUP].relation_joined, self._on_update_status
        )

        self.cluster_infra_backup = VeleroBackupRequirer(
            self,
            app_name="infra-backup",
            relation_name=CLUSTER_INFRA_BACKUP,
            spec=VeleroBackupSpec(
                include_namespaces=self._get_ns_infra_back_up(), include_cluster_resources=True
            ),
        )

    def _on_update_status(self, _: ops.EventBase) -> None:
        """Update the charm's status."""
        issues = []
        if not self.k8s_utils.has_enough_permission():
            issues.append("Missing '--trust': insufficient permissions")

        if not self._cluster_infra_backup_exist():
            issues.append(f"Missing relation: [{CLUSTER_INFRA_BACKUP}]")

        if issues:
            self.model.unit.status = ops.BlockedStatus("; ".join(issues))
        else:
            self.model.unit.status = ops.ActiveStatus("Ready")

    def _cluster_infra_backup_exist(self) -> bool:
        """Check if the relation for infra backup exists."""
        return bool(self.model.relations.get(CLUSTER_INFRA_BACKUP))

    def _get_ns_infra_back_up(self) -> list[str]:
        """Return sorted list of infra-related namespaces present in the cluster."""
        namespaces = self.k8s_utils.get_namespaces()
        infra_namespaces = sorted(namespaces & INFRA_NAMESPACES)
        return infra_namespaces


if __name__ == "__main__":  # pragma: nocover
    ops.main(InfraBackupOperatorCharm)
