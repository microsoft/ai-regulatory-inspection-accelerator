"""Tests for the generic REST inbound connector."""

import pytest

from connectors.rest.connector import RestConnector
from connectors.sdk.base_connector import ConnectorTransformError


def test_maps_external_case_id_to_request_id():
    payload = RestConnector({}).transform_submission({"caseId": "DEMO-42", "documents": []})

    assert payload["requestId"] == "DEMO-42"


def test_preserves_existing_request_id():
    payload = RestConnector({}).transform_submission({
        "caseId": "EXTERNAL-42",
        "requestId": "ARIA-42",
    })

    assert payload["requestId"] == "ARIA-42"


def test_rejects_non_object_payload():
    with pytest.raises(ConnectorTransformError):
        RestConnector({}).transform_submission([])