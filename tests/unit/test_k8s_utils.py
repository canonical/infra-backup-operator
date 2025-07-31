# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
from unittest.mock import MagicMock, patch

import httpx
import pytest

from k8s_utils import ApiError, K8sUtils, K8sUtilsError


@pytest.fixture(autouse=True)
def mock_lightkube_client() -> MagicMock:  # type: ignore[misc]
    with patch("k8s_utils.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        yield mock_instance


def make_api_error(message: str = "forbidden") -> ApiError:
    # Fake a minimal Response object
    mock_request = httpx.Request("GET", "http://k8s")
    mock_response = httpx.Response(
        status_code=403,
        request=mock_request,
        json={"message": message, "reason": "Forbidden", "code": 403},
    )

    return ApiError(request=mock_request, response=mock_response)


# def test_has_enough_permission_false(mock_lightkube_client: MagicMock) -> None:
#     mock_lightkube_client.list.side_effect = make_api_error()
#     utils = K8sUtils()
#     assert utils.has_enough_permission() is False


# def test_has_enough_permission_true(mock_lightkube_client: MagicMock) -> None:
#     mock_lightkube_client.list.return_value = [object()]
#     utils = K8sUtils()
#     assert utils.has_enough_permission() is True


def test_get_namespaces(mock_lightkube_client: MagicMock) -> None:
    ns1 = MagicMock()
    ns1.metadata.name = "default"
    ns2 = MagicMock()
    ns2.metadata.name = "kube-system"

    mock_lightkube_client.list.return_value = [ns1, ns2]
    utils = K8sUtils("infra-backup-operator")

    assert utils.get_namespaces() == {"default", "kube-system"}


def test_get_namespaces_error(mock_lightkube_client: MagicMock):
    mock_lightkube_client.list.side_effect = make_api_error()
    utils = K8sUtils("infra-backup-operator")
    with pytest.raises(K8sUtilsError):
        utils.get_namespaces()
