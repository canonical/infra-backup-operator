#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""The Infra Backup Charm."""

import logging

import ops
from k8s_utils import K8s
from charms.velero_libs.v0.velero_backup_config import VeleroBackupRequirer,VeleroBackupSpec

logger = logging.getLogger(__name__)

INFRA_NAMESPACES = {"kube-system", "kube-public", "metallb-system"}


class InfraBackupOperatorCharm(ops.CharmBase):
    """A charm for managing a K8s cluster infrastructure backup."""

    def __init__(self, framework: ops.Framework) -> None:
        """Initialise the Infra Backup charm."""
        super().__init__(framework)
        self.k8s = K8s()

    def _set_backup(self):
        """Set the backup configuration for velero."""
        self._set_cluster_infra_backup()

    def _set_cluster_infra_backup(self):
        """Set the cluster infra backup.

        This function sets the right configuration to backup all resources in the INFRA_NAMESPACES
        and also all cluster scoped resources (e.g., CRDs, CSRs, ClusterRoles and etc.)
        """
        infra_namespaces = list(self.k8s.get_namespaces().intersection(INFRA_NAMESPACES))
        self.user_workload_backup = VeleroBackupRequirer(
            self,
            app="infra-backup",
            endpoint="cluster-infra-backup",
            spec=VeleroBackupSpec(
                include_namespaces=infra_namespaces,
                include_cluster_resources=True
            )
        )


if __name__ == "__main__":  # pragma: nocover
    ops.main(InfraBackupOperatorCharm)
