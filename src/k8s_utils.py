# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility functions for Backup Infra."""

import logging

import httpx
from lightkube import ApiError, Client
from lightkube.resources.core_v1 import Namespace

logger = logging.getLogger(__name__)


class K8sUtilsError(Exception):
    """Custom exception for K8sUtils errors."""


class K8sUtils:
    """K8s utils information using lightkube."""

    def __init__(self, field_manage: str) -> None:
        self.client = Client(field_manager=field_manage)

    def get_namespaces(self) -> set[str]:
        """Get the namespaces available in the K8s cluster.

        Returns:
            set[str]: Set of strings with the namespaces names.
        """
        try:
            return {namespace.metadata.name for namespace in self.client.list(Namespace)}
        except (ApiError, httpx.HTTPError) as e:
            raise K8sUtilsError("Failed to list namespaces") from e
