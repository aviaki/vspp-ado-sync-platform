"""
ADO client helpers — async, paginated, retry-aware.

This module:

* wraps Azure DevOps REST calls with exponential-back-off retry
* paginates large result sets via WIQL + continuation tokens
* fetches work-items in chunks (to stay under URL length limits)
"""

from __future__ import annotations

import asyncio
import base64
import random
import time
from typing import AsyncIterator, Iterable, List

import httpx

from ..core.config import get_settings

# ────────────────────────── constants ──────────────────────────────
_SETTINGS = get_settings()
_TRANSIENT = {429, 500, 502, 503, 504}
_API_VER = "7.1"
_CHUNK_IDS = 190  # each work-items batch (= <= ~8 KB URL)


# ────────────────────────── helpers ────────────────────────────────
def _auth_header(pat: str) -> dict[str, str]:
    """Basic-auth header from PAT (username = empty)."""
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json: dict | None = None,
    max_retries: int = 5,
    backoff: float = 1.0,
    timeout: float = 60.0,
) -> httpx.Response:
    """HTTP request with exponential-jitter back-off on transient codes."""
    hdrs = {"Accept": "application/json", **headers}
    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.request(
                method,
                url,
                headers=hdrs,
                json=json,
                timeout=timeout,
            )
            if resp.status_code not in _TRANSIENT:
                resp.raise_for_status()
                return resp
        except httpx.RequestError:
            # network / TLS etc.
            pass

        # transient failure → back-off and retry
        sleep = backoff * (2 ** (attempt - 1)) * random.uniform(0.8, 1.2)
        await asyncio.sleep(min(sleep, 30))

    # last attempt raised or still transient → raise
    resp.raise_for_status()
    return resp  # for type-checker only


# ─────────────────────── WIQL pagination ───────────────────────────
async def _iter_ids(
    *,
    pat: str,
    org: str,
    project: str,
    wi_type: str,
    states: list[str] | None,
    page_size: int = 2000,
) -> AsyncIterator[int]:
    """
    Yield work-item IDs of a given type / state filter, using WIQL
    continuation tokens for pagination.
    """
    hdr = _auth_header(pat) | {"Content-Type": "application/json"}

    state_clause = ""
    if states:
        joined = " OR ".join(f\"[System.State] = '{s}'\" for s in states)
        state_clause = f"AND ({joined})"

    wiql_body = {
        "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
              AND [System.WorkItemType] = '{wi_type}'
              {state_clause}
            ORDER BY [System.Id] ASC
        """
    }

    cont_token: str | None = None
    async with httpx.AsyncClient(base_url=f"https://dev.azure.com/{org}") as client:
        while True:
            url = (
                f"/{project}/_apis/wit/wiql?api-version={_API_VER}"
                f"&$top={page_size}"
                + (f"&continuationToken={cont_token}" if cont_token else "")
            )
            resp = await _request_with_retry(
                client, "POST", url, headers=hdr, json=wiql_body
            )
            data = resp.json()
            for wi in data.get("workItems", []):
                yield wi["id"]

            cont_token = data.get("continuationToken")
            if not cont_token:
                break


async def _fetch_items(
    *,
    pat: str,
    org: str,
    project: str,
    ids: Iterable[int],
    expand: str = "all",
    chunk: int = _CHUNK_IDS,
) -> list[dict]:
    """Fetch work-items by ID chunks (<= URL length limit)."""
    hdr = _auth_header(pat)
    items: list[dict] = []

    async with httpx.AsyncClient(base_url=f"https://dev.azure.com/{org}") as client:
        ids_list = list(ids)
        for i in range(0, len(ids_list), chunk):
            block = ",".join(map(str, ids_list[i : i + chunk]))
            url = (
                f"/{project}/_apis/wit/workitems"
                f"?ids={block}&api-version={_API_VER}&$expand={expand}"
            )
            resp = await _request_with_retry(client, "GET", url, headers=hdr)
            items.extend(resp.json().get("value", []))

    return items


# ─────────────────── high-level public helpers ──────────────────────
async def fetch_mk_feature_requests(states: list[str] | None = None) -> list[dict]:
    """Return MK Feature Request items (optionally filtered by state)."""
    s = _SETTINGS
    ids = [
        wid
        async for wid in _iter_ids(
            pat=s.mk_ado_pat,
            org=s.mk_ado_org,
            project=s.mk_ado_project,
            wi_type="Feature Request",
            states=states,
        )
    ]
    if not ids:
        return []
    return await _fetch_items(
        pat=s.mk_ado_pat,
        org=s.mk_ado_org,
        project=s.mk_ado_project,
        ids=ids,
    )


async def fetch_tm_epics(states: list[str] | None = None) -> list[dict]:
    """Return TM Epic items (optionally filtered by state)."""
    s = _SETTINGS
    ids = [
        wid
        async for wid in _iter_ids(
            pat=s.tm_ado_pat,
            org=s.tm_ado_org,
            project=s.tm_ado_project,
            wi_type="Epic",
            states=states,
        )
    ]
    if not ids:
        return []
    return await _fetch_items(
        pat=s.tm_ado_pat,
        org=s.tm_ado_org,
        project=s.tm_ado_project,
        ids=ids,
    )

