"""Application logging setup.

Uvicorn configures its own `uvicorn.*` loggers but installs no handler that shows *our* logs, so
under `uvicorn`/`make dev` an app-level `logger.warning(...)` vanishes. That's not cosmetic here:
the `ConsoleEmailService` fallback prints the verification code through exactly such a warning, and
its whole reason to exist — testing signup before a mail provider is configured — depends on that
line being visible.

We give the top-level `app` logger its own stream handler so our logs show up under uvicorn, which
otherwise leaves them handler-less and silent. Propagation is left on (the default): uvicorn installs
no root handler, so there's nothing to double-log through, and keeping it on means pytest's `caplog`
still captures app-level records through the root logger.
"""

import logging

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """Attach a stream handler to the `app` logger. Idempotent across reloads."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logger = logging.getLogger("app")
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    logger.addHandler(handler)
    _CONFIGURED = True
