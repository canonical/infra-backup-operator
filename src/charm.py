#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""The Infra Backup Charm."""

import logging
from typing import Optional

import ops
from charms.velero_libs.v0.velero_backup_config import VeleroBackupRequirer, VeleroBackupSpec

from k8s_utils import K8sUtils, K8sUtilsError
from literals import (
    CLUSTER_INFRA_BACKUP,
    NAMESPACED_INFRA_BACKUP,
    RESOURCES_BACKUP,
    InfraBackupConfig,
)

logger = logging.getLogger(__name__)


class InfraBackupOperatorCharm(ops.CharmBase):
    """A charm for managing a K8s cluster infrastructure backup."""

    def __init__(self, framework: ops.Framework) -> None:
        """Initialise the Infra Backup charm."""
        super().__init__(framework)
        self.k8s_utils = K8sUtils(self.unit.app.name)
        self.setup_failure: Optional[ops.StatusBase] = None
        self.cluster_infra_backup: Optional[VeleroBackupRequirer] = None
        self.namespaced_infra_backup: Optional[VeleroBackupRequirer] = None

        self.framework.observe(self.on.install, self._assess_cluster_backup_state)
        self.framework.observe(self.on.config_changed, self._assess_cluster_backup_state)
        self.framework.observe(self.on.update_status, self._assess_cluster_backup_state)
        self.framework.observe(self.on.upgrade_charm, self._assess_cluster_backup_state)
        for relation in [CLUSTER_INFRA_BACKUP, NAMESPACED_INFRA_BACKUP]:
            self.framework.observe(
                self.on[relation].relation_joined, self._assess_cluster_backup_state
            )
            self.framework.observe(
                self.on[relation].relation_broken, self._assess_cluster_backup_state
            )

        self._setup_cluster_infra_backup()
        self._set_namespaced_infra_backup()

    def _assess_cluster_backup_state(self, _: ops.EventBase) -> None:
        """Update the charm's status."""
        missing_relations = []

        if self.setup_failure:
            self.model.unit.status = self.setup_failure
            return

        for relation in [CLUSTER_INFRA_BACKUP, NAMESPACED_INFRA_BACKUP]:
            if not self._relation_exist(relation):
                missing_relations.append(relation)

        if missing_relations:
            self.model.unit.status = ops.BlockedStatus(
                f"Missing relation(s): {', '.join(missing_relations)}"
            )

        else:
            self.model.unit.status = ops.ActiveStatus("Ready")

    def _setup_cluster_infra_backup(self) -> None:
        """Set up the relation for cluster-infra-backup.

        Persistent Volumes are not backed up because it is workload related and applications
        should be responsible for configuring the backup.

        Pods are ephemeral and are automatically recreated by higher-level controllers
        e.g: Deployments, StatefulSets, and DaemonSets.
        """
        try:
            cluster_namespaces = self.k8s_utils.get_namespaces()
        except K8sUtilsError as e:
            logger.error("Failed to get the cluster namespaces: %s", e)
            self.setup_failure = ops.WaitingStatus("Trying to get namespaces...")
            return

        try:
            config = self.load_config(InfraBackupConfig)
        except ValueError as e:
            logger.error("Invalid charm namespace config: %s", e)
            self.setup_failure = ops.BlockedStatus(str(e))
            return

        backup_namespaces = sorted(cluster_namespaces & config.backup_namespaces)
        self.cluster_infra_backup = VeleroBackupRequirer(
            self,
            app_name=self.unit.app.name,
            relation_name=CLUSTER_INFRA_BACKUP,
            spec=VeleroBackupSpec(
                include_namespaces=backup_namespaces,
                exclude_resources=["persistentvolumes", "pods"],
                include_cluster_resources=True,
            ),
            refresh_event=[self.on.update_status, self.on.config_changed],
        )

    def _set_namespaced_infra_backup(self) -> None:
        """Set up the relation for namespaced-infra-backup.

        Sets up the relation to ensure that all critical namespaced Kubernetes resources (e.g:
        Roles, RoleBindings, NetworkPolicies, Secrets) are included in the backup across all
        namespaces. This is essential for preserving cluster functionality and security
        configurations.
        """
        self.namespaced_infra_backup = VeleroBackupRequirer(
            self,
            app_name=self.unit.app.name,
            relation_name=NAMESPACED_INFRA_BACKUP,
            spec=VeleroBackupSpec(include_resources=RESOURCES_BACKUP),
            refresh_event=[self.on.upgrade_charm],
        )

    def _relation_exist(self, relation: str) -> bool:
        """Check if a relation exists."""
        return bool(self.model.relations.get(relation))


if __name__ == "__main__":  # pragma: nocover
    ops.main(InfraBackupOperatorCharm)
