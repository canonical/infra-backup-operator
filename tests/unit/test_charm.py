# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
from unittest.mock import MagicMock, patch

import pytest
from ops import testing
from pytest_mock import MockerFixture
from scenario import Relation

from charm import InfraBackupOperatorCharm, K8sUtilsError
from literals import CLUSTER_INFRA_BACKUP


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
        "charm.InfraBackupOperatorCharm._cluster_infra_backup_exist",
        return_value=cluster_infra_backup_set,
    )
    ctx = testing.Context(InfraBackupOperatorCharm)

    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.BlockedStatus(msg)


def test_assess_cluster_backup_state_active(
    charm_state: testing.State, mocker: MockerFixture
) -> None:
    mocker.patch(
        "charm.InfraBackupOperatorCharm._cluster_infra_backup_exist",
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
):
    mocker.patch(
        "charm.InfraBackupOperatorCharm.load_config",
        side_effect=ValueError("wrong config"),
    )
    ctx = testing.Context(InfraBackupOperatorCharm)
    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.BlockedStatus("wrong config")


@pytest.mark.parametrize(
    "testing_state, expected",
    [
        (testing.State(), False),
        (
            testing.State(
                relations=[
                    Relation(
                        endpoint=CLUSTER_INFRA_BACKUP,
                        remote_app_data={
                            "spec": '{"include_namespaces":["kube-public","kube-system"]'
                        },
                    )
                ]
            ),
            True,
        ),
    ],
    ids=[
        "Without cluster-infra-backup relation returns False",
        "With cluster-infra-backup relation returns True",
    ],
)
def test_cluster_infra_backup_exist_true(testing_state: testing.State, expected: bool) -> None:
    ctx = testing.Context(InfraBackupOperatorCharm)
    with ctx(ctx.on.start(), testing_state) as manager:
        cluster_infra_backup = manager.charm._cluster_infra_backup_exist()
    assert cluster_infra_backup is expected


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
def test_wrong_namespace_config(namespaces, exp_msg):
    ctx = testing.Context(InfraBackupOperatorCharm)
    state_in = testing.State(config={"namespaces": namespaces})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    assert state_out.unit_status == testing.BlockedStatus(exp_msg)
