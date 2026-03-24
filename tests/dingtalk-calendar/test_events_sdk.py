"""
阶段二：SDK 测试 — calendar_1_0 日程事件 CRUD + 列表

主日历 calendarId 使用 primary。路径中的 userId 为 unionId。
"""
import time
from datetime import datetime, timedelta, timezone

import pytest
from alibabacloud_dingtalk.calendar_1_0 import models as cal_models


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _sdk_create_event(sdk_client, sdk_runtime, token, union_id, primary_calendar_id, summary: str) -> str:
    h = cal_models.CreateEventHeaders()
    h.x_acs_dingtalk_access_token = token
    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=2)
    end = start + timedelta(hours=1)
    req = cal_models.CreateEventRequest(
        summary=summary,
        description="pytest dingtalk-calendar",
        start=cal_models.CreateEventRequestStart(
            date_time=_iso_utc(start),
            time_zone="UTC",
        ),
        end=cal_models.CreateEventRequestEnd(
            date_time=_iso_utc(end),
            time_zone="UTC",
        ),
    )
    resp = sdk_client.create_event_with_options(union_id, primary_calendar_id, req, h, sdk_runtime)
    assert resp.body and resp.body.id, f"创建日程无 id：{resp.body}"
    return resp.body.id


def _sdk_delete_event(sdk_client, sdk_runtime, token, union_id, primary_calendar_id, event_id: str) -> None:
    h = cal_models.DeleteEventHeaders()
    h.x_acs_dingtalk_access_token = token
    req = cal_models.DeleteEventRequest()
    sdk_client.delete_event_with_options(union_id, primary_calendar_id, event_id, req, h, sdk_runtime)


def test_sdk_event_create_get_patch_list_delete(
    sdk_client, sdk_runtime, token, union_id, primary_calendar_id
):
    """创建 → 查询 → 列表(时间窗) → 更新 → 删除"""
    summary = f"[sdk] cal {int(time.time())}"
    event_id = _sdk_create_event(
        sdk_client, sdk_runtime, token, union_id, primary_calendar_id, summary
    )

    try:
        gh = cal_models.GetEventHeaders()
        gh.x_acs_dingtalk_access_token = token
        greq = cal_models.GetEventRequest()
        gresp = sdk_client.get_event_with_options(
            union_id, primary_calendar_id, event_id, greq, gh, sdk_runtime
        )
        assert gresp.body and gresp.body.id == event_id
        assert gresp.body.summary == summary

        now = datetime.now(timezone.utc)
        tmin = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        tmax = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        lh = cal_models.ListEventsHeaders()
        lh.x_acs_dingtalk_access_token = token
        lreq = cal_models.ListEventsRequest(
            time_min=tmin,
            time_max=tmax,
            max_results=50,
        )
        lresp = sdk_client.list_events_with_options(
            union_id, primary_calendar_id, lreq, lh, sdk_runtime
        )
        assert lresp.body is not None
        ids = [e.id for e in (lresp.body.events or []) if e and e.id]
        assert event_id in ids, f"列表中未找到新建日程 id，样本: {ids[:5]}"

        ph = cal_models.PatchEventHeaders()
        ph.x_acs_dingtalk_access_token = token
        new_summary = summary + " [patched]"
        preq = cal_models.PatchEventRequest(id=event_id, summary=new_summary)
        presp = sdk_client.patch_event_with_options(
            union_id, primary_calendar_id, event_id, preq, ph, sdk_runtime
        )
        assert presp.body is not None and presp.body.summary == new_summary
    finally:
        _sdk_delete_event(sdk_client, sdk_runtime, token, union_id, primary_calendar_id, event_id)
