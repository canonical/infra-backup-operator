# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
from unittest.mock import MagicMock, patch

import pytest
from ops import testing
from pytest_mock import MockerFixture
from scenario import Relation

from charm import InfraBackupOperatorCharm, K8sUtilsError
from literals import CLUSTER_INFRA_BACKUP, NAMESPACED_INFRA_BACKUP


@pytest.fixture(autouse=True)
def mock_k8s_utils() -> MagicMock:  # type: ignore[misc]
    with patch("charm.K8sUtils") as mock_k8s_utils:
        mock_instance = MagicMock()
        mock_k8s_utils.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def charm_state() -> testing.State:  # type: ignore[misc]
    yield testing.State(leader=True)


@pytest.mark.parametrize(
    "cluster_infra_backup_set, msg",
    [
        (False, f"Missing relation: [{CLUSTER_INFRA_BACKUP}]"),
    ],
    ids=[
        "Not relating cluster-infra-backup ep blocks the charm",
    ],
)
def test_assess_cluster_backup_state_block(
    charm_state: testing.State,
    mocker: MockerFixture,
    cluster_infra_backup_set: bool,
    msg: str,
) -> None:
    mocker.patch(
        "charm.InfraBackupOperatorCharm._relation_exist",
        return_value=cluster_infra_backup_set,
    )
    ctx = testing.Context(InfraBackupOperatorCharm)

    mock_k8s_utils.has_enough_permission.return_value = permission

    ctx = testing.Context(InfraBackupOperatorCharm)
    state_out = ctx.run(ctx.on.update_status(), charm_state)

    assert state_out.unit_status == testing.BlockedStatus(expected_msg)


def test_assess_cluster_backup_state_active(
    charm_state: testing.State, mocker: MockerFixture
) -> None:
    mocker.patch(
        "charm.InfraBackupOperatorCharm._relation_exist",
        return_value=True,
    )
    ctx = testing.Context(InfraBackupOperatorCharm)

    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.ActiveStatus("Ready")


def test_assess_cluster_backup_state_waiting_fail_ns(
    mock_k8s_utils: MagicMock, charm_state: testing.State
) -> None:
    mock_k8s_utils.get_namespaces.side_effect = K8sUtilsError("wrong permission")
    ctx = testing.Context(InfraBackupOperatorCharm)
    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.WaitingStatus("Trying to get namespaces...")


def test_assess_cluster_backup_state_block_wrong_config(
    mocker: MockerFixture, charm_state: testing.State
) -> None:
    mocker.patch(
        "charm.InfraBackupOperatorCharm.load_config",
        side_effect=ValueError("wrong config"),
    )
    ctx = testing.Context(InfraBackupOperatorCharm)
    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.BlockedStatus("wrong config")


@pytest.mark.parametrize(
    "relation_name, endpoint, expected",
    [
        # No relations
        (CLUSTER_INFRA_BACKUP, None, False),
        # Only cluster-infra present
        (CLUSTER_INFRA_BACKUP, CLUSTER_INFRA_BACKUP, True),
        (CLUSTER_INFRA_BACKUP, NAMESPACED_INFRA_BACKUP, False),
    ],
    ids=["no-cluster", "only-cluster (checking cluster)", "only-namespaced (checking cluster)"],
)
def test_relation_exist(relation_name: str, endpoint: str, expected: bool) -> None:
    ctx = testing.Context(InfraBackupOperatorCharm)
    testing_state = testing.State(relations=[Relation(endpoint=endpoint)] if endpoint else [])

    with ctx(ctx.on.start(), testing_state) as manager:
        result = manager.charm._relation_exist(relation_name)
    assert result is expected


@pytest.mark.parametrize(
    "namespaces, exp_msg",
    [
        ("", "The namespaces config cannot be empty"),
        ("-my-namespace", "Invalid namespace name: '-my-namespace'"),
        ("my-namespace-", "Invalid namespace name: 'my-namespace-'"),
        ("My-namespace", "Invalid namespace name: 'My-namespace'"),
    ],
    ids=[
        "Empty namespaces",
        "namespace starting with '-'",
        "namespace ending with '-'",
        "namespace starting with capital letter",
    ],
)
def test_wrong_namespace_config(namespaces: str, exp_msg: str) -> None:
    ctx = testing.Context(InfraBackupOperatorCharm)
    state_in = testing.State(config={"namespaces": namespaces})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    assert state_out.unit_status == testing.BlockedStatus(exp_msg)
