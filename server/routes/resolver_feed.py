"""
Resolver Feed API — Exposes canonical Salesforce resolver datasets for CGB selectors.

Returns pre-formatted records from CMG_Account.csv via AccountIndex,
enabling the Contract Generator to prefer canonical Salesforce data over
workbook-derived fallback rows.
"""
import logging
from fastapi import APIRouter, Query
from typing import Optional

from server.resolvers.account_index import get_index

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2.5/resolver", tags=["resolver-feed"])


@router.get("/accounts")
def list_resolver_accounts(
    q: Optional[str] = Query(None, description="Optional search filter"),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    idx = get_index()
    if not idx.loaded:
        return {"data": [], "total": 0, "source": "salesforce_resolver", "loaded": False}

    all_recs = idx.all_records()
    total = len(all_recs)

    if q and q.strip():
        from server.resolvers.account_index import normalize
        q_norm = normalize(q)
        filtered = []
        for rec in all_recs:
            if any(q_norm in n for n in rec.normalized_names):
                filtered.append(rec)
            elif q_norm in normalize(rec.account_id):
                filtered.append(rec)
            elif q_norm in normalize(rec.id_18):
                filtered.append(rec)
        all_recs = filtered
        total = len(all_recs)

    page = all_recs[offset:offset + limit]
    return {
        "data": [
            {
                "account_name": r.account_name,
                "display_name": r.display_name,
                "type": r.type,
                "account_id": r.account_id,
                "id_18": r.id_18,
                "le_id": r.le_id,
                "artist_name": r.artist_name,
                "company_name": r.company_name,
                "legal_name": r.legal_name,
            }
            for r in page
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
        "source": "salesforce_resolver",
        "loaded": True,
    }


@router.get("/accounts/summary")
def resolver_accounts_summary():
    idx = get_index()
    if not idx.loaded:
        return {"loaded": False, "total": 0, "types": {}}

    all_recs = idx.all_records()
    type_counts = {}
    for r in all_recs:
        t = r.type or "Unknown"
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "loaded": True,
        "total": len(all_recs),
        "types": type_counts,
        "source": "salesforce_resolver",
    }
