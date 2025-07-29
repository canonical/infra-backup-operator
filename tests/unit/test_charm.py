# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
from unittest.mock import MagicMock, patch

import pytest
from ops import testing
from pytest_mock import MockerFixture
from scenario import Relation

from charm import CLUSTER_INFRA_BACKUP, NAMESPACED_INFRA_BACKUP, InfraBackupOperatorCharm


@pytest.fixture(autouse=True)
def mock_k8s_utils() -> MagicMock:  # type: ignore[misc]
    with patch("charm.K8sUtils") as mock_k8s_utils:
        mock_instance = MagicMock()
        mock_k8s_utils.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def charm_state() -> testing.State:  # type: ignore[misc]
    yield testing.State(leader=True)


def test_assess_cluster_backup_state_missing_permission(
    mock_k8s_utils: MagicMock, charm_state: testing.State, mocker: MockerFixture
) -> None:
    mocker.patch("charm.InfraBackupOperatorCharm._relation_exist", return_value=True)
    mock_k8s_utils.has_enough_permission.return_value = False
    ctx = testing.Context(InfraBackupOperatorCharm)

    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.BlockedStatus(
        "Missing '--trust': insufficient permissions"
    )


@pytest.mark.parametrize(
    "relations_exist, permission, expected_msg",
    [
        # Only missing trust
        ([True, True], False, "Missing '--trust': insufficient permissions"),
        # Only one relation missing
        ([False, True], True, f"Missing relation: [{CLUSTER_INFRA_BACKUP}]"),
        ([True, False], True, f"Missing relation: [{NAMESPACED_INFRA_BACKUP}]"),
        # Both relations missing
        (
            [False, False],
            True,
            f"Missing relation: [{CLUSTER_INFRA_BACKUP}]; "
            f"Missing relation: [{NAMESPACED_INFRA_BACKUP}]",
        ),
        # Missing both trust and relations
        (
            [False, False],
            False,
            "Missing '--trust': insufficient permissions; "
            f"Missing relation: [{CLUSTER_INFRA_BACKUP}]; "
            f"Missing relation: [{NAMESPACED_INFRA_BACKUP}]",
        ),
    ],
    ids=[
        "Missing only trust",
        "Missing cluster-infra relation",
        "Missing namespaced-infra relation",
        "Missing both relations",
        "Missing trust and both relations",
    ],
)
def test_assess_cluster_backup_state_block(
    mock_k8s_utils: MagicMock,
    charm_state: testing.State,
    mocker: MockerFixture,
    relations_exist: list[bool],
    permission: bool,
    expected_msg: str,
) -> None:
    mocker.patch(
        "charm.InfraBackupOperatorCharm._relation_exist",
        side_effect=relations_exist,
    )

    mock_k8s_utils.has_enough_permission.return_value = permission

    ctx = testing.Context(InfraBackupOperatorCharm)
    state_out = ctx.run(ctx.on.update_status(), charm_state)

    assert state_out.unit_status == testing.BlockedStatus(expected_msg)


def test_assess_cluster_backup_state_active(
    mock_k8s_utils: MagicMock, charm_state: testing.State, mocker: MockerFixture
) -> None:
    mocker.patch(
        "charm.InfraBackupOperatorCharm._relation_exist",
        return_value=True,
    )
    mock_k8s_utils.has_enough_permission.return_value = True
    ctx = testing.Context(InfraBackupOperatorCharm)

    state_out = ctx.run(ctx.on.update_status(), charm_state)
    assert state_out.unit_status == testing.ActiveStatus("Ready")


@pytest.mark.parametrize(
    "relation_name, testing_state, expected",
    [
        # No relations
        (CLUSTER_INFRA_BACKUP, testing.State(), False),
        (NAMESPACED_INFRA_BACKUP, testing.State(), False),
        # Only cluster-infra present
        (
            CLUSTER_INFRA_BACKUP,
            testing.State(relations=[Relation(endpoint=CLUSTER_INFRA_BACKUP)]),
            True,
        ),
        (
            NAMESPACED_INFRA_BACKUP,
            testing.State(relations=[Relation(endpoint=CLUSTER_INFRA_BACKUP)]),
            False,
        ),
        # Only namespaced-infra present
        (
            CLUSTER_INFRA_BACKUP,
            testing.State(relations=[Relation(endpoint=NAMESPACED_INFRA_BACKUP)]),
            False,
        ),
        (
            NAMESPACED_INFRA_BACKUP,
            testing.State(relations=[Relation(endpoint=NAMESPACED_INFRA_BACKUP)]),
            True,
        ),
    ],
    ids=[
        "no-cluster",
        "no-namespaced",
        "only-cluster (checking cluster)",
        "only-cluster (checking namespaced)",
        "only-namespaced (checking cluster)",
        "only-namespaced (checking namespaced)",
    ],
)
def test_relation_exist(relation_name: str, testing_state: testing.State, expected: bool) -> None:
    ctx = testing.Context(InfraBackupOperatorCharm)
    with ctx(ctx.on.start(), testing_state) as manager:
        result = manager.charm._relation_exist(relation_name)
    assert result is expected
