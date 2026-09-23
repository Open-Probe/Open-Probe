"""
Sonic credential resolution.

`SONIC_JWT` carries the credential; `SONIC_AUTH_MODE` *declares* which kind it is:

    SONIC_AUTH_MODE=jwt   (default)  Entra OAuth/JWT. Production-legal.
    SONIC_AUTH_MODE=pat             Personal Access Token. Testing only.

The default is `jwt`, so a PAT -- a testing-only credential by policy -- has to be
opted into. A PAT left in a production config then fails at startup instead of
working until someone audits it.

Sonic itself discriminates the two structurally (a three-part token is a JWT) and
accepts either in `Authorization: Bearer`, so the declared mode never changes what
goes on the wire. It exists to catch the mismatch *locally*: sent to Sonic, a PAT
where a JWT was intended comes back as a bare `401 Invalid API Key.` on the first
real call, which says nothing about which credential it wanted.

What the mode is for:

- Validating the credential's shape against the declared intent, here.
- Telling a long-lived process whether to build a token-refresh path. JWTs last
  about an hour; PATs are static. Nothing in this repo refreshes yet -- every
  entrypoint is a short-lived process -- so `auth_mode()` is currently reported
  rather than acted on.
- Making the production gate assertable: deployment config can require
  `SONIC_AUTH_MODE=jwt`, which shape-sniffing cannot express, because a deliberate
  PAT and an accidental one are byte-identical.

Do **not** branch on the mode to choose a header. The credential goes only in the
OpenAI `api_key` slot (`Authorization: Bearer`), which takes either type; an
`api-key` header is checked first by Sonic as a PAT-only lookup and 401s a JWT
before `Authorization` is read.

This module is a leaf on purpose, for the same reason `sonic_tls` is: it imports
nothing from the rest of `deepsearch`, so `evals/` can use it without dragging in
`graph.py` (which pulls torch and downloads a multi-gigabyte fasttext model at
import).
"""

import os
from typing import Tuple

VALID_AUTH_MODES = ("jwt", "pat")

_PAT_HINT = (
    "For testing, issue a Personal Access Token from the Sonic Self-Service Auth "
    "Manager and set SONIC_AUTH_MODE=pat. Production traffic requires an Entra "
    "OAuth/JWT token, which is the default mode."
)


def _looks_like_jwt(token: str) -> bool:
    """
    Structural JWT test, matching the one Sonic applies server-side.

    A JWT is three non-empty dot-separated parts. Anything else is treated as a PAT.
    """
    parts = token.split(".")
    return len(parts) == 3 and all(part.strip() for part in parts)


def auth_mode() -> str:
    """The declared credential type: ``"jwt"`` (the default) or ``"pat"``."""
    mode = (os.getenv("SONIC_AUTH_MODE") or "jwt").strip().lower()
    if mode not in VALID_AUTH_MODES:
        raise ValueError(
            f"SONIC_AUTH_MODE is {mode!r}; expected "
            f"{' or '.join(repr(m) for m in VALID_AUTH_MODES)}."
        )
    return mode


def sonic_credential() -> Tuple[str, str]:
    """
    Return ``(credential, mode)``, raising if the two disagree.

    Raises ValueError when SONIC_JWT is unset, when SONIC_AUTH_MODE is not a valid
    mode, or when the credential's shape contradicts the declared mode.
    """
    mode = auth_mode()
    declared = "SONIC_AUTH_MODE" in os.environ and bool(os.environ["SONIC_AUTH_MODE"].strip())

    token = os.getenv("SONIC_JWT")
    if not token:
        raise ValueError(f"SONIC_JWT is not set. {_PAT_HINT}")
    token = token.strip()

    looks_like_jwt = _looks_like_jwt(token)
    if mode == "jwt" and not looks_like_jwt:
        which = "'jwt'" if declared else "'jwt' (the default)"
        raise ValueError(
            f"SONIC_AUTH_MODE is {which} but SONIC_JWT is not a three-part JWT. "
            "Set SONIC_AUTH_MODE=pat if you are testing with a Personal Access "
            "Token, or supply an Entra OAuth/JWT token."
        )
    if mode == "pat" and looks_like_jwt:
        raise ValueError(
            "SONIC_AUTH_MODE is 'pat' but SONIC_JWT looks like a three-part JWT. "
            "Set SONIC_AUTH_MODE=jwt."
        )

    return token, mode
