#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging
import pprint
from typing import Any, Callable, Optional

import yaml
from jubilant import Juju
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

from literals import ROLES_RESOURCE, VELERO_CHARM, VELERO_ENDPOINT
from src.literals import RESOURCES_BACKUP

logger = logging.getLogger(__name__)

config.load_kube_config()
v1 = client.CoreV1Api()
rbac_v1 = client.RbacAuthorizationV1Api()


def create_namespace(name: str) -> None:
    """Create the namespace only if it doesn't already exist."""
    try:
        v1.read_namespace(name=name)
        logger.info(f"Namespace '{name}' already exists. Skipping the creation.")
    except ApiException as e:
        if e.status == 404:
            namespace = client.V1Namespace(metadata=client.V1ObjectMeta(name=name))
            v1.create_namespace(body=namespace)
            logger.info(f"Namespace '{name}' created.")
        else:
            raise


def delete_namespace(name: str) -> None:
    """Delete the namespace only if exists."""
    try:
        v1.read_namespace(name=name)
    except ApiException as e:
        if e.status == 404:
            logger.info(f"Namespace '{name}' does not exist. Skipping delete.")
            return
        else:
            raise

    try:
        v1.delete_namespace(name=name)
        logger.info(f"Namespace '{name}' deletion initiated.")
    except ApiException as e:
        logger.error(f"Failed to delete namespace '{name}': {e}")
        raise


def list_roles_clusterroles(namespace: str = "default") -> dict[str, set]:
    config.load_kube_config()
    rbac_v1 = client.RbacAuthorizationV1Api()
    roles = {
        role.metadata.name for role in rbac_v1.list_namespaced_role(namespace=namespace).items
    }
    cluster_roles = {
        cluster_role.metadata.name for cluster_role in rbac_v1.list_cluster_role().items
    }
    return {"roles": roles, "cluster_roles": cluster_roles}


def get_velero_spec(juju: Juju, endpoint: str) -> dict[str, Any]:
    """Get the velero spec in the relation."""
    velero_unit = list(juju.status().apps[VELERO_CHARM].units.keys())[0]
    data = yaml.safe_load(juju.cli("show-unit", velero_unit))
    app_data_bag = get_app_data_bag(velero_unit, data, endpoint)
    return json.loads(app_data_bag["application-data"]["spec"])


def get_app_data_bag(unit: str, data: dict[str, Any], endpoint: str) -> dict[str, Any]:
    """Get the application data bag of Velero Operator where it will configure the backup."""
    relation_data = [v for v in data[unit]["relation-info"] if v["endpoint"] == VELERO_ENDPOINT]
    if len(relation_data) == 0:
        raise ValueError(f"No data found for relation {VELERO_ENDPOINT}")
    for relation in relation_data:
        if relation["related-endpoint"] == endpoint:
            return relation
    raise ValueError(f"No data found for endpoint {endpoint}")


def get_expected_infra_backup_data_bag(extra_ns: Optional[list[str]] = None) -> dict:
    ns = ["kube-public", "kube-system"]
    if extra_ns:
        ns = sorted(ns + extra_ns)
    return {
        "include_namespaces": ns,
        "include_resources": None,
        "exclude_namespaces": None,
        "exclude_resources": RESOURCES_BACKUP + ["persistentvolumes", "pods"],
        "label_selector": None,
        "ttl": None,
        "include_cluster_resources": True,
    }


def get_expected_namespaced_infra_backup_data_bag() -> dict:
    return {
        "include_namespaces": None,
        "include_resources": RESOURCES_BACKUP,
        "exclude_namespaces": None,
        "exclude_resources": None,
        "label_selector": None,
        "ttl": None,
        "include_cluster_resources": None,
    }


# Retry for up to 60 seconds, every 10 seconds, only if AssertionError is raised
@retry(
    stop=stop_after_delay(60),
    wait=wait_fixed(10),
    retry=retry_if_exception_type(AssertionError),
    reraise=True,
)
def wait_for_backup_spec(func: Callable, expected_spec: dict) -> None:
    velero_spec = func()
    if velero_spec != expected_spec:
        raise AssertionError(
            "Backup spec mismatch:\n"
            f"Actual:\n{pprint.pformat(velero_spec)}\n\n"
            f"Expected:\n{pprint.pformat(expected_spec)}"
        )


def create_pod_reader_role() -> None:
    logger.info("Creating role: %s", ROLES_RESOURCE)
    role = client.V1Role(
        metadata=client.V1ObjectMeta(name=ROLES_RESOURCE),
        rules=[
            client.V1PolicyRule(
                api_groups=[""], resources=["pods"], verbs=["get", "watch", "list"]
            )
        ],
    )
    rbac_v1.create_namespaced_role(body=role, namespace="default")


def create_pod_reader_cluster_role() -> None:
    logger.info("Creating cluster role: %s", ROLES_RESOURCE)
    cluster_role = client.V1ClusterRole(
        metadata=client.V1ObjectMeta(name=ROLES_RESOURCE),
        rules=[
            client.V1PolicyRule(
                api_groups=[""], resources=["pods"], verbs=["get", "list", "watch"]
            )
        ],
    )
    rbac_v1.create_cluster_role(body=cluster_role)


def delete_pod_reader_role() -> None:
    logger.info("Deleting role: %s", ROLES_RESOURCE)
    rbac_v1.delete_namespaced_role(name=ROLES_RESOURCE, namespace="default")


def delete_pod_reader_cluster_role() -> None:
    logger.info("Deleting cluster role: %s", ROLES_RESOURCE)
    rbac_v1.delete_cluster_role(name=ROLES_RESOURCE)
