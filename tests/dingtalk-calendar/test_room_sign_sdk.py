"""
会议室忙闲、签到/签退链接与操作 — SDK（calendar_1_0）

- 会议室忙闲：需环境变量 TEST_MEETING_ROOM_IDS（逗号分隔 roomId），否则 skip。
- 签到链接等：先创建临时日程，再调接口，最后删除。
"""
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
from alibabacloud_dingtalk.calendar_1_0 import models as cal_models
from darabonba.exceptions import UnretryableException


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _sdk_create_event(sdk_client, sdk_runtime, token, union_id, cal_id: str, summary: str) -> str:
    h = cal_models.CreateEventHeaders()
    h.x_acs_dingtalk_access_token = token
    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=3)
    end = start + timedelta(hours=1)
    req = cal_models.CreateEventRequest(
        summary=summary,
        start=cal_models.CreateEventRequestStart(date_time=_iso(start), time_zone="UTC"),
        end=cal_models.CreateEventRequestEnd(date_time=_iso(end), time_zone="UTC"),
    )
    resp = sdk_client.create_event_with_options(union_id, cal_id, req, h, sdk_runtime)
    assert resp.body and resp.body.id
    return resp.body.id


def _sdk_delete_event(sdk_client, sdk_runtime, token, union_id, cal_id: str, event_id: str) -> None:
    dh = cal_models.DeleteEventHeaders()
    dh.x_acs_dingtalk_access_token = token
    dr = cal_models.DeleteEventRequest()
    sdk_client.delete_event_with_options(union_id, cal_id, event_id, dr, dh, sdk_runtime)


def test_sdk_meeting_rooms_schedule(sdk_client, sdk_runtime, token, union_id):
    raw = os.environ.get("TEST_MEETING_ROOM_IDS", "").strip()
    if not raw:
        pytest.skip("未设置 TEST_MEETING_ROOM_IDS（逗号分隔的会议室 roomId，用于忙闲查询）")
    room_ids = [x.strip() for x in raw.split(",") if x.strip()]
    if not room_ids:
        pytest.skip("TEST_MEETING_ROOM_IDS 为空")

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    hh = cal_models.GetMeetingRoomsScheduleHeaders()
    hh.x_acs_dingtalk_access_token = token
    req = cal_models.GetMeetingRoomsScheduleRequest(
        start_time=_iso(start),
        end_time=_iso(end),
        room_ids=room_ids,
    )
    try:
        resp = sdk_client.get_meeting_rooms_schedule_with_options(union_id, req, hh, sdk_runtime)
    except UnretryableException as e:
        if "403" in str(e) or "400" in str(e):
            pytest.skip(f"会议室忙闲不可用：{str(e)[:200]}")
        raise
    assert resp.body is not None


def test_sdk_sign_in_out_links_and_ops(sdk_client, sdk_runtime, token, union_id, primary_calendar_id):
    """获取签到/签退链接；尝试签到、签退（若业务不允许则跳过）。"""
    eid = _sdk_create_event(
        sdk_client,
        sdk_runtime,
        token,
        union_id,
        primary_calendar_id,
        f"[pytest-room-sign] {int(time.time())}",
    )
    try:
        th = cal_models.GetSignInLinkHeaders()
        th.x_acs_dingtalk_access_token = token
        # SDK 参数顺序：(calendarId, userId, eventId) → URL 为 users/{userId}/calendars/{calendarId}/...
        in_resp = sdk_client.get_sign_in_link_with_options(
            primary_calendar_id, union_id, eid, th, sdk_runtime
        )
        assert in_resp.body and in_resp.body.sign_in_link

        toh = cal_models.GetSignOutLinkHeaders()
        toh.x_acs_dingtalk_access_token = token
        out_resp = sdk_client.get_sign_out_link_with_options(
            primary_calendar_id, union_id, eid, toh, sdk_runtime
        )
        assert out_resp.body and out_resp.body.sign_out_link

        sih = cal_models.SignInHeaders()
        sih.x_acs_dingtalk_access_token = token
        try:
            sir = sdk_client.sign_in_with_options(union_id, primary_calendar_id, eid, sih, sdk_runtime)
            assert sir.body is not None
        except UnretryableException as e:
            if "400" in str(e) or "403" in str(e):
                pytest.skip(f"日程不支持 API 签到或条件未满足：{str(e)[:180]}")
            raise

        soh = cal_models.SignOutHeaders()
        soh.x_acs_dingtalk_access_token = token
        try:
            sor = sdk_client.sign_out_with_options(union_id, primary_calendar_id, eid, soh, sdk_runtime)
            assert sor.body is not None
        except UnretryableException as e:
            if "400" in str(e) or "403" in str(e):
                pytest.skip(f"签退跳过：{str(e)[:180]}")
            raise
    finally:
        _sdk_delete_event(sdk_client, sdk_runtime, token, union_id, primary_calendar_id, eid)
