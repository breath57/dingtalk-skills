"""
dingtalk-contact 专属 fixture
"""
import os
import pytest


@pytest.fixture(scope="session")
def my_user_id() -> str:
    """返回操作者自身的 userId（整数字符串）。"""
    val = os.environ.get("DINGTALK_MY_USER_ID", "")
    if not val:
        pytest.skip("缺少环境变量 DINGTALK_MY_USER_ID")
    return val


@pytest.fixture(scope="session")
def operator_id() -> str:
    """返回操作者自身的 unionId（DINGTALK_MY_OPERATOR_ID）。"""
    val = os.environ.get("DINGTALK_MY_OPERATOR_ID", "")
    if not val:
        pytest.skip("缺少环境变量 DINGTALK_MY_OPERATOR_ID")
    return val
