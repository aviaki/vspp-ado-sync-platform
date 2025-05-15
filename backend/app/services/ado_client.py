"""
ado_client.py – async helper for Azure DevOps REST

• Handles robust HTTP retries with exponential back-off.
• Supports WIQL pagination (continuationToken) so we never
  blow request-length limits.
• Bulk-fetches work-item payloads in chunks (≤ 200 IDs).
• Two public helpers:
      ‣ fetch_mk_feature_requests(states: list[str] | None)
      ‣ fetch_tm_epics(states: list[str] | None)
  … both return a list[dict] containing the full ADO JSON.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import AsyncIterator, Sequence

import httpx
from httpx import Response

from ..core.config import get_settings

# ───────────────────────── constants ──────────────────────────
_API_VER = "7.1"
_ID_PAGE_SIZE = 200            # page size for WIQL ID fetch
_BATCH_CHUNK = 190             # <=200 ids/query is ADO limit - small margin
_MAX_RETRIES = 5
_TRANSIENT = {429, 500, 502, 503, 504}

settings = get_settings()

# ───────────────────────── helpers ────────────────────────────


def _auth_header(pat: str) -> dict[str, str]:
    """
    Azure DevOps PAT → Basic auth header.
    Username may be blank; PAT goes in password slot.
    """
    from base64 import b64encode

    token = b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict | None = None,
    max_retries: int = _MAX_RETRIES,
    timeout: float = 60.0,
) -> Response:
    """HTTP with exponential jittered back-off on transient errors."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.request(
                method,
                url,
                headers=headers,
                json=json_body,
                timeout=timeout,
            )

            if resp.status_code not in _TRANSIENT:
                resp.raise_for_status()
                return resp

        except httpx.RequestError:
            # network / DNS error, treat as transient
            pass

        # back-off – capped exponential with jitter
        sleep = min(30.0, (2 ** (attempt - 1)) * random.uniform(0.8, 1.2))
        await asyncio.sleep(sleep)

    # still failing
    resp.raise_for_status()  # type: ignore  (resp guaranteed to exist)


# ─────────── iterate IDs with WIQL pagination ────────────────
async def _iter_ids(
    client: httpx.AsyncClient,
    org: str,
    project: str,
    pat: str,
    work_item_type: str,
    states: Sequence[str] | None = None,
) -> AsyncIterator[int]:
    """
    Yield work-item IDs for a given type/state filter.

    Uses continuationToken so it works for large result sets.
    """
    # Build optional state clause
    state_clause = ""
    if states:
        joined = " OR ".join(f"[System.State] = '{s}'" for s in states)
        state_clause = f"AND ({joined})"

    query = f"""
        SELECT  [System.Id]
        FROM    WorkItems
        WHERE   [System.TeamProject] = '{project}'
            AND [System.WorkItemType] = '{work_item_type}'
            {state_clause}
        ORDER BY [System.Id] ASC
    """.strip()

    body = {"query": query}
    token: str | None = None
    hdr = _auth_header(pat)

    while True:
        url = (
            f"https://dev.azure.com/{org}/{project}/_apis/wit/wiql"
            f"?$top={_ID_PAGE_SIZE}&api-version={_API_VER}"
        )
        if token:
            url += f"&continuationToken={token}"

        resp = await _request_with_retry(client, "POST", url, headers=hdr, json_body=body)
        data = resp.json()

        for wi in data.get("workItems", []):
            yield wi["id"]

        token = data.get("continuationToken")
        if not token:
            break


# ───────────── bulk-fetch full work-item docs ────────────────
async def _fetch_items(
    client: httpx.AsyncClient,
    org: str,
    project: str,
    pat: str,
    ids: list[int],
) -> list[dict]:
    hdr = _auth_header(pat)
    out: list[dict] = []

    for i in range(0, len(ids), _BATCH_CHUNK):
        block = ",".join(map(str, ids[i : i + _BATCH_CHUNK]))
        url = (
            f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems"
            f"?ids={block}&$expand=all&api-version={_API_VER}"
        )
        resp = await _request_with_retry(client, "GET", url, headers=hdr)
        out.extend(resp.json().get("value", []))

    return out


# ───────────── public convenience wrappers ───────────────────
async def fetch_mk_feature_requests(states: Sequence[str] | None = None) -> list[dict]:
    """Return full MK Feature-Request docs matching *states*."""
    org = settings.mk_ado_org
    project = settings.mk_ado_project
    pat = settings.mk_ado_pat

    async with httpx.AsyncClient() as client:
        ids = [
            wid
            async for wid in _iter_ids(
                client, org, project, pat, work_item_type="Feature Request", states=states
            )
        ]
        if not ids:
            return []

        return await _fetch_items(client, org, project, pat, ids)


async def fetch_tm_epics(states: Sequence[str] | None = None) -> list[dict]:
    """Return full TM Epic docs matching *states*."""
    org = settings.tm_ado_org
    project = settings.tm_ado_project
    pat = settings.tm_ado_pat

    async with httpx.AsyncClient() as client:
        ids = [
            wid
            async for wid in _iter_ids(
                client, org, project, pat, work_item_type="Epic", states=states
            )
        ]
        if not ids:
            return []

        return await _fetch_items(client, org, project, pat, ids)

