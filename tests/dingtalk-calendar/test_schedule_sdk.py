"""
阶段一/二探针：calendar_1_0 — 查询闲忙 GetSchedule（querySchedule）

所需权限以开放平台实际返回为准；403 时 skip 并提示开通权限。
"""
from datetime import datetime, timedelta, timezone

import pytest
from alibabacloud_dingtalk.calendar_1_0 import models as cal_models


def test_sdk_get_schedule(sdk_client, sdk_runtime, token, union_id):
    """POST /v1.0/calendar/users/{unionId}/querySchedule — 查询闲忙"""
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    # 接口要求完整 ISO8601（含毫秒），否则 400 ParsedISO8601TimestampError
    fmt = "%Y-%m-%dT%H:%M:%S.000Z"

    h = cal_models.GetScheduleHeaders()
    h.x_acs_dingtalk_access_token = token
    req = cal_models.GetScheduleRequest(
        start_time=start.strftime(fmt),
        end_time=end.strftime(fmt),
        user_ids=[union_id],
    )
    try:
        resp = sdk_client.get_schedule_with_options(union_id, req, h, sdk_runtime)
    except Exception as e:
        msg = str(e)
        if "403" in msg or "AccessDenied" in msg:
            pytest.skip(f"缺少日程相关权限或未开通：{msg[:200]}")
        raise

    assert resp.body is not None, "响应 body 为空"
