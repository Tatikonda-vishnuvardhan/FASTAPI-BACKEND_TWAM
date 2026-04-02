"""
Angular GridService compatibility layer.

Angular sends:
  page.index=1 & page.size=20 & order.property=name & order.ascending=true
  & filters[0].property=brandName & filters[0].comparison=contains & filters[0].value=test

NOTE: page.size=0 is allowed — Angular uses it to mean "fetch all" or "default size".
      Repositories should treat 0 as None (no limit) or use their own default.
"""

import re
from typing import Optional, List, Dict
from fastapi import Query, Request


class GridParams:
    def __init__(
        self,
        request: Request,
        page_index:      Optional[int]  = Query(None, alias="page.index"),
        page_size:       Optional[int]  = Query(None, alias="page.size"),
        order_property:  Optional[str]  = Query(None, alias="order.property"),
        order_ascending: Optional[bool] = Query(None, alias="order.ascending"),
    ):
        self.page_index      = page_index if (page_index and page_index > 0) else None
        self.page_size       = page_size  if (page_size  and page_size  > 0) else None
        self.order_property  = order_property or None
        self.order_ascending = order_ascending
        self.filters         = self._parse_filters(request)

    def _parse_filters(self, request: Request) -> Optional[List[Dict]]:
        raw    = dict(request.query_params)
        bucket: Dict[int, Dict] = {}

        for key, value in raw.items():
            m = re.match(r'filters\[(\d+)\]\.(\w+)$', key, re.IGNORECASE)
            if m:
                idx   = int(m.group(1))
                field = m.group(2).lower()
                if idx not in bucket:
                    bucket[idx] = {}
                bucket[idx][field] = value

        if not bucket:
            return None

        result = []
        for i in sorted(bucket.keys()):
            f = bucket[i]
            if f.get("property") and f.get("value") not in (None, ""):
                result.append({
                    "property":   f["property"],
                    "comparison": f.get("comparison", "contains"),
                    "value":      f["value"],
                })
        return result or None
