# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
from unittest.mock import MagicMock, patch

import pytest
from ops import testing
from scenario import Relation

from charm import CLUSTER_INFRA_BACKUP, InfraBackupOperatorCharm


@pytest.fixture(autouse=True)
def mock_k8s_utils():
    with patch("charm.K8sUtils") as mock_k8s_utils:
        mock_instance = MagicMock()
        mock_k8s_utils.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def charm_state():
    yield testing.State(leader=True)


def test_on_update_status_missing_permission(mock_k8s_utils, charm_state, mocker):
    mocker.patch("charm.InfraBackupOperatorCharm._cluster_infra_backup_exist", return_value=True)
    mock_k8s_utils.has_enough_permission.return_value = False
    ctx = testing.Context(InfraBackupOperatorCharm)

    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.BlockedStatus(
        "Missing '--trust': insufficient permissions"
    )


@pytest.mark.parametrize(
    "cluster_infra_backup_set, permission, msg",
    [
        (True, False, "Missing '--trust': insufficient permissions"),
        (False, True, f"Missing relation: [{CLUSTER_INFRA_BACKUP}]"),
        (
            False,
            False,
            (
                "Missing '--trust': insufficient permissions; "
                f"Missing relation: [{CLUSTER_INFRA_BACKUP}]"
            ),
        ),
    ],
    ids=[
        "Deploying without --trust blocks the charm",
        "Not relating cluster-infra-backup ep blocks the charm",
        "Block message collects more than one issue",
    ],
)
def test_on_update_status_block(
    mock_k8s_utils, charm_state, mocker, cluster_infra_backup_set, permission, msg
):
    mocker.patch(
        "charm.InfraBackupOperatorCharm._cluster_infra_backup_exist",
        return_value=cluster_infra_backup_set,
    )
    mock_k8s_utils.has_enough_permission.return_value = permission
    ctx = testing.Context(InfraBackupOperatorCharm)

    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.BlockedStatus(msg)


def test_on_update_status_active(mock_k8s_utils, charm_state, mocker):
    mocker.patch(
        "charm.InfraBackupOperatorCharm._cluster_infra_backup_exist",
        return_value=True,
    )
    mock_k8s_utils.has_enough_permission.return_value = True
    ctx = testing.Context(InfraBackupOperatorCharm)

    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.ActiveStatus("Ready")


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
def test_cluster_infra_backup_exist_true(testing_state, expected):
    ctx = testing.Context(InfraBackupOperatorCharm)
    with ctx(ctx.on.start(), testing_state) as manager:
        cluster_infra_backup = manager.charm._cluster_infra_backup_exist()
    assert cluster_infra_backup is expected
