"""
阶段三：纯 HTTP 测试 — 日程事件与闲忙（requests）

BASE: https://api.dingtalk.com/v1.0/calendar
"""
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
import requests

BASE = "https://api.dingtalk.com/v1.0/calendar"


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _http_create(union_id, primary_calendar_id, headers: dict, summary: str) -> str:
    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=2)
    end = start + timedelta(hours=1)
    body = {
        "summary": summary,
        "description": "pytest http calendar",
        "start": {"dateTime": _iso_utc(start), "timeZone": "UTC"},
        "end": {"dateTime": _iso_utc(end), "timeZone": "UTC"},
    }
    url = f"{BASE}/users/{union_id}/calendars/{primary_calendar_id}/events"
    r = requests.post(url, headers=headers, json=body, timeout=20)
    assert r.status_code == 200, f"创建失败 {r.status_code}: {r.text}"
    data = r.json()
    assert data.get("id"), f"无 id：{data}"
    return data["id"]


def _http_delete(union_id, primary_calendar_id, headers: dict, event_id: str) -> None:
    url = f"{BASE}/users/{union_id}/calendars/{primary_calendar_id}/events/{event_id}"
    r = requests.delete(url, headers=headers, timeout=20)
    assert r.status_code == 200, f"删除失败 {r.status_code}: {r.text}"


def test_http_event_flow(union_id, primary_calendar_id, api_headers):
    """HTTP：创建 → GET → GET列表 → PUT → DELETE"""
    summary = f"[http] cal {int(time.time())}"
    event_id = _http_create(union_id, primary_calendar_id, api_headers, summary)
    try:
        url_get = f"{BASE}/users/{union_id}/calendars/{primary_calendar_id}/events/{event_id}"
        r = requests.get(url_get, headers=api_headers, timeout=20)
        assert r.status_code == 200
        assert r.json().get("id") == event_id
        assert r.json().get("summary") == summary

        now = datetime.now(timezone.utc)
        tmin = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        tmax = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        q = urlencode({"timeMin": tmin, "timeMax": tmax, "maxResults": 50})
        url_list = f"{BASE}/users/{union_id}/calendars/{primary_calendar_id}/events?{q}"
        r2 = requests.get(url_list, headers=api_headers, timeout=20)
        assert r2.status_code == 200
        events = r2.json().get("events") or []
        ids = [e.get("id") for e in events if e.get("id")]
        assert event_id in ids

        new_summary = summary + " [patched]"
        url_put = url_get
        r3 = requests.put(
            url_put,
            headers=api_headers,
            json={"id": event_id, "summary": new_summary},
            timeout=20,
        )
        assert r3.status_code == 200, r3.text
        assert r3.json().get("summary") == new_summary
    finally:
        _http_delete(union_id, primary_calendar_id, api_headers, event_id)


def test_http_query_schedule(union_id, api_headers):
    """POST .../users/{unionId}/querySchedule 闲忙"""
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    url = f"{BASE}/users/{union_id}/querySchedule"
    body = {
        "startTime": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endTime": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "userIds": [union_id],
    }
    r = requests.post(url, headers=api_headers, json=body, timeout=20)
    if r.status_code == 403:
        pytest.skip(f"缺少闲忙权限: {r.text[:200]}")
    assert r.status_code == 200, r.text
