# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility functions for Backup Infra."""

from lightkube import Client
from lightkube.resources.core_v1 import Namespace

class K8s:
    def __init__(self):
        self.client = Client(field_manager="infra-backup-operator")

    def get_namespaces(self) -> set[str]:
        return {namespace.metadata.name for namespace in self.client.list(Namespace)}
