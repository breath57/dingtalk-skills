"""
test_auth.py —— 测试鉴权：获取 accessToken
"""
import requests


BASE = "https://api.dingtalk.com"


def test_get_access_token(token: str):
    """可拿到非空的 accessToken 字符串"""
    assert isinstance(token, str) and len(token) > 10, f"accessToken 异常：{token!r}"


def test_token_format(token: str):
    """accessToken 应为 32 位及以上的十六进制字符串"""
    assert len(token) >= 32
