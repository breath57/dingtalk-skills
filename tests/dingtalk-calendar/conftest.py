"""
dingtalk-calendar 测试专属 fixtures
  - union_id: 操作者 unionId（与 OPERATOR_ID / DINGTALK_MY_OPERATOR_ID 一致）
  - primary_calendar_id: 主日历固定为字符串 primary（与开放平台行为一致）

API 基础路径：/v1.0/calendar/...
认证：x-acs-dingtalk-access-token（新版 OAuth2）
"""
import pytest
from alibabacloud_dingtalk.calendar_1_0 import client as cal_client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models


@pytest.fixture(scope="session")
def union_id(operator_id) -> str:
    return operator_id


@pytest.fixture(scope="session")
def primary_calendar_id() -> str:
    """主日历 ID，创建/查询日程时使用。"""
    return "primary"


@pytest.fixture(scope="session")
def sdk_client():
    config = open_api_models.Config()
    config.protocol = "HTTPS"
    config.endpoint = "api.dingtalk.com"
    return cal_client.Client(config)


@pytest.fixture(scope="session")
def sdk_runtime():
    return util_models.RuntimeOptions()
