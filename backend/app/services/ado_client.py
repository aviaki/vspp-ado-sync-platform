import base64, httpx
from typing import List, Dict
from ..core.config import get_settings
s = get_settings()
def _auth(pat): return {"Authorization": f"Basic {base64.b64encode(f':{pat}'.encode()).decode()}"}
async def fetch_mk_feature_requests(states: List[str]) -> List[Dict]:
    q = ("Select [System.Id] From WorkItems Where [System.TeamProject]='{proj}' "
         "And [System.WorkItemType]='Feature Request' And [System.State] In ({states})").format(
        proj=s.mk_ado_project, states=", ".join([f"'{st}'" for st in states]))
    wiql_url = f"https://dev.azure.com/{s.mk_ado_org}/{s.mk_ado_project}/_apis/wit/wiql?api-version=7.1"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(wiql_url, json={"query": q}, headers=_auth(s.mk_ado_pat)); r.raise_for_status()
        ids = [str(i["id"]) for i in r.json()["workItems"]]
        if not ids: return []
        items_url = f"https://dev.azure.com/{s.mk_ado_org}/{s.mk_ado_project}/_apis/wit/workitems?ids={','.join(ids)}&api-version=7.1"
        i = await c.get(items_url, headers=_auth(s.mk_ado_pat)); i.raise_for_status()
        return i.json()["value"]
