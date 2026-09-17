"""
TLS trust for Sonic.

Sonic may be served off a *private*, internal PKI rather than a public CA.

The OpenAI SDK talks over httpx, and httpx verifies against certifi, which does
not and never will carry such a root. Without help every Sonic call dies as a bare
`openai.APIConnectionError: Connection error.` -- the real
`ssl.SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED ... self-signed
certificate in certificate chain` is buried several `raise ... from` layers down,
so the message you actually see says nothing about certificates.

This bites unevenly, which is what makes it easy to miss: `curl` and `urllib`
resolve against the OS trust store, where a managed laptop already trusts the
internal root, so hand-probing Sonic succeeds while the agent fails. Most
containers trust neither.

Resolution order:

1. ``SONIC_CA_BUNDLE`` -- path to a PEM holding the internal roots.
   Deterministic and explicit; the right choice for containers and CI.
2. The OS trust store, via ``truststore``. Works unmodified on a corporate
   managed host.
3. httpx's certifi default. Only correct if Sonic is ever fronted by a public
   CA, and kept as the fallback so this module can never be the thing that
   breaks an already-working setup.

There is deliberately **no** "skip verification" switch. Turning off TLS
verification against a gateway carrying prompts and completions is not a
shortcut worth shipping; to debug a chain, point ``SONIC_CA_BUNDLE`` at it.

This module is a leaf on purpose: it imports nothing from the rest of
`deepsearch`, so `evals/` can use it without dragging in `graph.py` (which pulls
torch and downloads a multi-gigabyte fasttext model at import).
"""

import os
import ssl
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple


def _ca_bundle() -> Optional[str]:
    """Return the SONIC_CA_BUNDLE path, or None. Raises if it is set but wrong."""
    bundle = os.getenv("SONIC_CA_BUNDLE")
    if not bundle:
        return None
    if not os.path.isfile(bundle):
        raise ValueError(
            f"SONIC_CA_BUNDLE points at {bundle!r}, which is not a file. Set it to "
            "a PEM bundle containing your organization's internal PKI roots, or "
            "unset it to fall back to the OS trust store."
        )
    return bundle


@lru_cache(maxsize=1)
def _resolve() -> Tuple[str, Any]:
    """
    Decide how to verify Sonic's certificate.

    Returns (source_label, verify) where `verify` is whatever httpx should be
    handed, or None to mean "leave httpx alone".
    """
    bundle = _ca_bundle()
    if bundle:
        return f"CA bundle {bundle}", bundle

    try:
        import truststore
    except ImportError:
        return ("certifi (default) -- no SONIC_CA_BUNDLE and truststore is not "
                "installed; expect a connection error if Sonic is on a private CA"), None

    # truststore.SSLContext subclasses ssl.SSLContext and delegates verification
    # to the platform. Scoped to these clients rather than the process, so we do
    # not change TLS behaviour for Serper, Jina, or crawl4ai.
    return "OS trust store (truststore)", truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


@lru_cache(maxsize=1)
def _clients() -> Tuple[Any, Any]:
    """Build the shared httpx client pair once per process."""
    _, verify = _resolve()
    if verify is None:
        return None, None
    try:
        import httpx
    except ImportError:  # pragma: no cover -- httpx ships with the openai SDK
        return None, None
    return httpx.Client(verify=verify), httpx.AsyncClient(verify=verify)


def trust_source() -> str:
    """Human-readable description of where Sonic's trust anchors come from."""
    return _resolve()[0]


def sonic_http_clients() -> Dict[str, Any]:
    """
    Keyword arguments giving a Sonic client the right trust anchors.

    Returns ``{}`` when nothing needs overriding, so callers can splat it
    unconditionally::

        ChatOpenAI(model=..., api_key=..., base_url=..., **sonic_http_clients())

    Both the sync and async clients are set. Every call site in the graph is
    currently sync, but leaving ``http_async_client`` unset would mean a future
    ``ainvoke`` silently reverted to certifi and failed.
    """
    sync_client, async_client = _clients()
    if sync_client is None:
        return {}
    return {"http_client": sync_client, "http_async_client": async_client}
