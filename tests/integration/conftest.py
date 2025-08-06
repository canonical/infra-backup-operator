# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import dataclasses
import json
import logging
import socket
import subprocess
import uuid

import boto3
import botocore.exceptions
import pytest
from kubernetes import client, config
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

MICROCEPH_BUCKET = "testbucket"
MICROCEPH_RGW_PORT = 7480
K8S_TEST_NAMESPACE = "velero-integration-tests"
K8S_TEST_PVC_RESOURCE_NAME = "test-pvc"
K8S_TEST_PVC_FILE_PATH = "test-file"

logger = logging.getLogger(__name__)

config.load_kube_config()
rbac_v1 = client.RbacAuthorizationV1Api()


@dataclasses.dataclass(frozen=True)
class S3ConnectionInfo:
    access_key_id: str
    secret_access_key: str
    bucket: str


def get_host_ip() -> str:
    """Figure out the host IP address accessible from pods in CI."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(botocore.exceptions.EndpointConnectionError),
    reraise=True,
)
def create_microceph_bucket(
    bucket_name: str, access_key: str, secret_key: str, endpoint: str
) -> None:
    """Attempt to create a bucket in MicroCeph with retry logic."""
    logger.info("Attempting to create microceph bucket")
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    s3_client.create_bucket(Bucket=bucket_name)


@pytest.fixture(scope="session")
def s3_connection_info() -> S3ConnectionInfo:
    """Return S3 connection info based on environment."""
    logger.info("Setting up microceph")

    try:
        subprocess.run(["sudo", "snap", "install", "microceph"], check=True)
        subprocess.run(["sudo", "microceph", "cluster", "bootstrap"], check=True)
        subprocess.run(["sudo", "microceph", "disk", "add", "loop,1G,3"], check=True)
        subprocess.run(
            ["sudo", "microceph", "enable", "rgw", "--port", str(MICROCEPH_RGW_PORT)], check=True
        )
        output = subprocess.run(
            [
                "sudo",
                "microceph.radosgw-admin",
                "user",
                "create",
                "--uid",
                "test",
                "--display-name",
                "test",
            ],
            capture_output=True,
            check=True,
            encoding="utf-8",
        ).stdout

        key = json.loads(output)["keys"][0]
        access_key = key["access_key"]
        secret_key = key["secret_key"]

        logger.info("Creating microceph bucket")
        create_microceph_bucket(
            MICROCEPH_BUCKET, access_key, secret_key, f"http://localhost:{MICROCEPH_RGW_PORT}"
        )

        logger.info("Set up microceph successfully")
        yield S3ConnectionInfo(access_key, secret_key, MICROCEPH_BUCKET)

    finally:
        logger.info("Cleaning up microceph")
        subprocess.run(["sudo", "snap", "remove", "--purge", "microceph"], check=False)


@pytest.fixture(scope="session")
def s3_cloud_credentials(
    s3_connection_info: S3ConnectionInfo,
) -> dict[str, str]:
    """Return cloud credentials for S3."""
    return {
        "access-key": s3_connection_info.access_key_id,
        "secret-key": s3_connection_info.secret_access_key,
    }


@pytest.fixture(scope="session")
def s3_cloud_configs(s3_connection_info: S3ConnectionInfo) -> dict[str, str]:
    """Return cloud configs for S3."""
    config = {
        "bucket": s3_connection_info.bucket,
        "path": f"velero/{uuid.uuid4()}",
    }

    config["endpoint"] = f"http://{get_host_ip()}:{MICROCEPH_RGW_PORT}"
    config["s3-uri-style"] = "path"
    config["region"] = "radosgw"

    return config
