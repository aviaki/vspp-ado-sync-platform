# backend/app/services/ado_client.py
"""
Azure DevOps client helpers – pagination-aware
──────────────────────────────────────────────
All helpers are *async* and designed to be used from the FastAPI
sync-daemon task.

Key points
──────────
• _iter_ids()  – lazy generator that pages through work-item IDs using
                 WIQL + continuationToken.
• _fetch_items() – pulls complete work-item docs in ≤200-ID batches.
• fetch_mk_feature_requests() / fetch_tm_epics() – convenience wrappers
  that query the respective ADO org/project from settings.

Any future ADO queries should build on _iter_ids() + _fetch_items() so
we never hit the 20 000-character URL or 200-ID API limits again.
"""
from __future__ import annotations

import asyncio
import base64
import random
import time
from typing import AsyncIterator, List

import httpx

from ..core.config import get_settings

# ---------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------

_TRANSIENT: set[int] = {429, 500, 502, 503, 504}
_CHUNK_IDS = 200            # max IDs per /workitems call
_PAGE_SIZE = 5000           # WIQL “$top”; bigger → fewer round-trips


def _auth_header(pat: str) -> dict[str, str]:
    """
    Azure DevOps PAT is sent via basic-auth with empty user-name.
    """
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json: dict | None = None,
    stream: bool = False,
    max_retries: int = 5,
    backoff: float = 1.0,
    timeout: float = 60.0,
) -> httpx.Response:
    """
    Tiny exponential-backoff retry wrapper for the handful of transient
    HTTP status codes ADO occasionally emits.
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.request(
                method,
                url,
                headers=headers,
                json=json,
                timeout=timeout,
                stream=stream,
            )
            if resp.status_code not in _TRANSIENT:
                resp.raise_for_status()
                return resp
        except (httpx.RequestError, httpx.HTTPStatusError):
            pass  # handled below

        # NB: don't hammer – jitter prevents thundering herd
        sleep = backoff * (2 ** (attempt - 1)) * random.uniform(0.8, 1.2)
        await asyncio.sleep(min(sleep, 30))

    # if we get here the last response still has error status
    resp.raise_for_status()  # will raise HTTPStatusError


async def _iter_ids(
    client: httpx.AsyncClient,
    *,
    org: str,
    project: str,
    pat: str,
    wiql: str,
) -> AsyncIterator[int]:
    """
    Yield *all* matching work-item IDs, transparently following the
    continuationToken that Azure DevOps returns when more rows are
    available.
    """
    hdr = {**_auth_header(pat), "Content-Type": "application/json"}
    cont: str | None = None

    while True:
        url = (
            f"https://dev.azure.com/{org}/{project}/_apis/wit/wiql"
            f"?api-version=7.1-preview&$top={_PAGE_SIZE}"
        )
        if cont:
            url += f"&continuationToken={cont}"

        resp = await _request_with_retry(
            client, "POST", url, headers=hdr, json={"query": wiql}
        )
        data = resp.json()

        for row in data.get("workItems", []):
            yield row["id"]

        cont = data.get("continuationToken")
        if not cont:
            break


async def _fetch_items(
    client: httpx.AsyncClient,
    *,
    org: str,
    project: str,
    pat: str,
    ids: List[int],
) -> List[dict]:
    """
    Fetch full work-item documents in compliant ≤200-ID batches and
    return them as a list.
    """
    hdr = _auth_header(pat)
    out: list[dict] = []

    for i in range(0, len(ids), _CHUNK_IDS):
        block = ",".join(map(str, ids[i : i + _CHUNK_IDS]))
        url = (
            f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems"
            f"?ids={block}&$expand=all&api-version=7.1-preview"
        )

        resp = await _request_with_retry(client, "GET", url, headers=hdr)
        out.extend(resp.json().get("value", []))

    return out


# ---------------------------------------------------------------------
# Public helpers used by sync_daemon.py
# ---------------------------------------------------------------------

async def fetch_mk_feature_requests(
    states: list[str] | None = None,
) -> list[dict]:
    """
    Return *all* MK Feature Request work-items matching the given
    states (or every state when `states is None`).
    """
    s = get_settings()
    wi_states = (
        " AND (" + " OR ".join(f"[System.State] = '{st}'" for st in states) + ")"
        if states
        else ""
    )

    wiql = (
        f"SELECT [System.Id] "
        f"FROM WorkItems "
        f"WHERE [System.TeamProject] = '{s.mk_ado_project}' "
        f"AND   [System.WorkItemType] = 'Feature Request' "
        f"{wi_states} "
        f"ORDER BY [System.Id] ASC"
    )

    async with httpx.AsyncClient() as client:
        ids = [wid async for wid in _iter_ids(
            client,
            org=s.mk_ado_org,
            project=s.mk_ado_project,
            pat=s.mk_ado_pat,
            wiql=wiql,
        )]

        if not ids:
            return []

        return await _fetch_items(
            client,
            org=s.mk_ado_org,
            project=s.mk_ado_project,
            pat=s.mk_ado_pat,
            ids=ids,
        )


async def fetch_tm_epics(states: list[str] | None = None) -> list[dict]:
    """
    Return TechMahindra EPICs, paginated exactly the same way.
    """
    s = get_settings()
    wi_states = (
        " AND (" + " OR ".join(f"[System.State] = '{st}'" for st in states) + ")"
        if states
        else ""
    )

    wiql = (
        f"SELECT [System.Id] "
        f"FROM WorkItems "
        f"WHERE [System.TeamProject] = '{s.tm_ado_project}' "
        f"AND   [System.WorkItemType] = 'Epic' "
        f"{wi_states} "
        f"ORDER BY [System.Id] ASC"
    )

    async with httpx.AsyncClient() as client:
        ids = [wid async for wid in _iter_ids(
            client,
            org=s.tm_ado_org,
            project=s.tm_ado_project,
            pat=s.tm_ado_pat,
            wiql=wiql,
        )]

        if not ids:
            return []

        return await _fetch_items(
            client,
            org=s.tm_ado_org,
            project=s.tm_ado_project,
            pat=s.tm_ado_pat,
            ids=ids,
        )

