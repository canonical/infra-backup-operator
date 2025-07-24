# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility functions for Backup Infra."""

import logging

from lightkube import ApiError, Client
from lightkube.resources.core_v1 import Namespace
from lightkube.resources.rbac_authorization_v1 import ClusterRole

logger = logging.getLogger(__name__)


class K8sUtils:
    """K8s utils information using lightkube."""

    def __init__(self):
        self.client = Client(field_manager="infra-backup-operator")

    def has_enough_permission(self) -> bool:
        """Check if the pod has enough permission for listing resources.

        Returns:
            bool: True if has enough permission, False otherwise
        """
        try:
            self.client.list(ClusterRole)
            self.client.list(Namespace)
            return True
        except ApiError as e:
            logger.debug("Missing permission to list ClusterRole: %s", e)
            return False

    def get_namespaces(self) -> set[str]:
        """Get the namespaces available in the K8s cluster.

        Returns:
            set[str]: Set of strings with the namespaces names.
        """
        return {namespace.metadata.name for namespace in self.client.list(Namespace)}
