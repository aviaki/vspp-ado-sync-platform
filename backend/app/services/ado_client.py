"""
ado_client.py
─────────────
Async helpers for talking to the two Azure DevOps orgs (MK & TM):

• automatic exponential-back-off on transient errors
• WIQL pagination via continuationToken
• chunked fetch of work-items (keeps URLs <8 kB)
"""

from __future__ import annotations

import asyncio
import base64
import random
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

import httpx

from ..core.config import get_settings

# ───────────────────────── constants ──────────────────────────
_TRANSIENT = {429, 500, 502, 503, 504}          # retry on these
_API_VER = "7.1"
_ID_PAGE_SIZE = 2000                            # WIQL page
_FETCH_CHUNK = 190                              # WS call ( <200 )


# ────────────────── helpers & retry wrapper ───────────────────
def _auth_header(pat: str) -> Dict[str, str]:
    tok = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {tok}"}


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: Dict[str, str],
    json_body: Dict | None = None,
    max_retries: int = 5,
    backoff: float = 1.0,
    timeout: float = 60.0,
) -> httpx.Response:
    """HTTP with exponential-jitter back-off on transient failures."""
    hdr = {"Accept": "application/json", **headers}
    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.request(method, url, headers=hdr, json=json_body, timeout=timeout)
            if resp.status_code not in _TRANSIENT:
                resp.raise_for_status()
                return resp
        except (httpx.RequestError, httpx.HTTPStatusError):
            if attempt == max_retries:
                raise
        sleep = backoff * (2 ** (attempt - 1)) * random.uniform(0.8, 1.2)
        await asyncio.sleep(min(sleep, 30))


# ─────────── iterate IDs with WIQL pagination ────────────────
async def _iter_ids(
    client: httpx.AsyncClient,
    org: str,
    project: str,
    pat: str,
    work_item_type: str,
    states: Optional[Sequence[str]] = None,
) -> AsyncIterator[int]:
    """Yield work-item IDs (handles continuationToken paging)."""
    state_clause = ""
    if states:
        joined = " OR ".join(f"[System.State] = '{s}'" for s in states)
        state_clause = f"AND ({joined})"

    body = {
        "query": f"""
        SELECT [System.Id]
        FROM WorkItems
        WHERE [System.TeamProject] = '{project}'
          AND [System.WorkItemType] = '{work_item_type}'
          {state_clause}
        ORDER BY [System.Id] ASC
        """
    }.strip()

    token: str | None = None
    hdr = _auth_header(pat)

    while True:
        url = f"https://dev.azure.com/{org}/{project}/_apis/wit/wiql?$top={_ID_PAGE_SIZE}&api-version={_API_VER}"
        if token:
            url += f"&continuationToken={token}"

        resp = await _request_with_retry(client, "POST", url, headers=hdr, json_body=body)
        data = resp.json()
        for wi in data.get("workItems", []):
            yield wi["id"]

        token = data.get("continuationToken")
        if not token:
            break


# ───────────── fetch items in manageable chunks ──────────────
async def _fetch_items(
    client: httpx.AsyncClient,
    org: str,
    project: str,
    pat: str,
    ids: List[int],
) -> List[Dict[str, Any]]:
    if not ids:
        return []

    hdr = _auth_header(pat)
    out: List[Dict[str, Any]] = []

    for i in range(0, len(ids), _FETCH_CHUNK):
        block = ",".join(map(str, ids[i : i + _FETCH_CHUNK]))
        url = (
            f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems"
            f"?ids={block}&$expand=all&api-version={_API_VER}"
        )
        resp = await _request_with_retry(client, "GET", url, headers=hdr)
        out.extend(resp.json().get("value", []))

    return out


# ─────────── high-level helpers used by daemon ───────────────
async def fetch_mk_feature_requests(states: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """Return MK Feature Requests (optionally filtered by state list)."""
    s = get_settings()
    async with httpx.AsyncClient() as client:
        ids = [
            wid
            async for wid in _iter_ids(
                client,
                s.mk_ado_org,
                s.mk_ado_project,
                s.mk_ado_pat,
                work_item_type="Feature Request",
                states=states,
            )
        ]
        return await _fetch_items(client, s.mk_ado_org, s.mk_ado_project, s.mk_ado_pat, ids)


async def fetch_tm_epics(states: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """Return TM EPICs (optionally filtered by state list)."""
    s = get_settings()
    async with httpx.AsyncClient() as client:
        ids = [
            wid
            async for wid in _iter_ids(
                client,
                s.tm_ado_org,
                s.tm_ado_project,
                s.tm_ado_pat,
                work_item_type="Epic",
                states=states,
            )
        ]
        return await _fetch_items(client, s.tm_ado_org, s.tm_ado_project, s.tm_ado_pat, ids)

