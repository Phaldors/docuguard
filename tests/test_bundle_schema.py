import pytest
from pydantic import ValidationError

from app.schemas.bundle import CreateDocumentBundleRequest


def test_bundle_request_strips_tenant_id_whitespace() -> None:
    request = CreateDocumentBundleRequest(tenant_id="  acme  ")

    assert request.tenant_id == "acme"


def test_bundle_request_rejects_blank_tenant_id() -> None:
    with pytest.raises(ValidationError):
        CreateDocumentBundleRequest(tenant_id="   ")
