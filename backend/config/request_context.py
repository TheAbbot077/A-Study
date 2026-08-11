from __future__ import annotations

import contextvars


request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
correlation_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)
