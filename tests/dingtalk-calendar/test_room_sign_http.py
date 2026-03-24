"""
会议室忙闲、签到/签退链接 — 纯 HTTP（requests）
"""
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE = "https://api.dingtalk.com/v1.0/calendar"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _create_event(union_id, primary_calendar_id, headers: dict) -> str:
    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=3)
    end = start + timedelta(hours=1)
    body = {
        "summary": f"[pytest-http-sign] {int(time.time())}",
        "start": {"dateTime": _iso(start), "timeZone": "UTC"},
        "end": {"dateTime": _iso(end), "timeZone": "UTC"},
    }
    url = f"{BASE}/users/{union_id}/calendars/{primary_calendar_id}/events"
    r = requests.post(url, headers=headers, json=body, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _delete_event(union_id, primary_calendar_id, headers: dict, event_id: str) -> None:
    url = f"{BASE}/users/{union_id}/calendars/{primary_calendar_id}/events/{event_id}"
    r = requests.delete(url, headers=headers, timeout=20)
    assert r.status_code == 200, r.text


def test_http_meeting_rooms_schedule(union_id, api_headers):
    raw = os.environ.get("TEST_MEETING_ROOM_IDS", "").strip()
    if not raw:
        pytest.skip("未设置 TEST_MEETING_ROOM_IDS")
    room_ids = [x.strip() for x in raw.split(",") if x.strip()]
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    url = f"{BASE}/users/{union_id}/meetingRooms/schedules/query"
    r = requests.post(
        url,
        headers=api_headers,
        json={
            "startTime": _iso(start),
            "endTime": _iso(end),
            "roomIds": room_ids,
        },
        timeout=20,
    )
    if r.status_code == 403:
        pytest.skip(r.text[:200])
    assert r.status_code == 200, r.text


def test_http_sign_links(union_id, primary_calendar_id, api_headers):
    eid = _create_event(union_id, primary_calendar_id, api_headers)
    try:
        base = f"{BASE}/users/{union_id}/calendars/{primary_calendar_id}/events/{eid}"
        r1 = requests.get(f"{base}/signInLinks", headers=api_headers, timeout=20)
        assert r1.status_code == 200, r1.text
        assert r1.json().get("signInLink")

        r2 = requests.get(f"{base}/signOutLinks", headers=api_headers, timeout=20)
        assert r2.status_code == 200, r2.text
        assert r2.json().get("signOutLink")
    finally:
        _delete_event(union_id, primary_calendar_id, api_headers, eid)
