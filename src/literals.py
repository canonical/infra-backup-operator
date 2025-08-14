# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Literals for the charm."""

import re
from dataclasses import dataclass

CLUSTER_INFRA_BACKUP = "cluster-infra-backup"
NAMESPACED_INFRA_BACKUP = "namespaced-infra-backup"
RESOURCES_BACKUP = [
    "roles",
    "rolebindings",
    "networkpolicies",
    "resourcequotas",
    "limitranges",
    "serviceaccounts",
    "gateways",
    "grpcroutes",
    "httproutes",
    "tlsroutes",
    "ingresses",
    "configmaps",
    "secrets",
    "cronjobs",
    "jobs",
    "horizontalpodautoscalers",
    "verticalpodautoscalers",
    "ciliumnetworkpolicies",
]


NAMESPACE_REGEX = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


@dataclass(frozen=True, kw_only=True)
class InfraBackupConfig:
    """Configuration for the Infra Backup charm."""

    namespaces: str = "kube-system, kube-public, metallb-system"
    """Comma-separated list of namespaces from the charm config."""

    def __post_init__(self) -> None:
        """Post init of InfraBackupConfig."""
        if not self.namespaces:
            raise ValueError("The namespaces config cannot be empty")

        namespaces = {ns.strip() for ns in self.namespaces.split(",") if ns.strip()}
        for ns in namespaces:
            if not NAMESPACE_REGEX.match(ns):
                raise ValueError(f"Invalid namespace name: '{ns}'")

    @property
    def backup_namespaces(self) -> set[str]:
        """Namespaces for backup the cluster infrastructure."""
        return {ns.strip() for ns in self.namespaces.split(",") if ns.strip()}
