from __future__ import annotations

import re
import uuid

from django.http import HttpRequest, HttpResponse

from .request_context import correlation_id_context, request_id_context

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


class RequestCorrelationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id, correlation_id = self._resolve_request_identifiers(request)
        request_id_token = request_id_context.set(request_id)
        correlation_id_token = correlation_id_context.set(correlation_id)
        request.request_id = request_id
        request.correlation_id = correlation_id
        try:
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = request_id
            response[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            request_id_context.reset(request_id_token)
            correlation_id_context.reset(correlation_id_token)

    def _resolve_request_identifiers(self, request: HttpRequest) -> tuple[str, str]:
        request_id = self._trusted_identifier(request.headers.get(REQUEST_ID_HEADER)) or str(uuid.uuid4())
        correlation_id = self._trusted_identifier(request.headers.get(CORRELATION_ID_HEADER)) or request_id
        return request_id, correlation_id

    def _trusted_identifier(self, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        if not value or not _SAFE_ID_RE.fullmatch(value):
            return None
        return value
