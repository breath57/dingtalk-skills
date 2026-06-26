#!/usr/bin/env python3
"""Small DingTalk knowledge CLI for Coding Agent workflows.

This is intentionally narrow: it does not crawl workspaces. It wraps the
official search API, reads one document by node/dentry id, and inspects blocks
for image-like attachment metadata.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import csv
import fcntl
import hashlib
import json
import mimetypes
import os
import re
import signal
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from io import StringIO
from typing import Any, cast


API_BASE = "https://api.dingtalk.com"


class DingTalkError(RuntimeError):
    pass


class LoginRequired(DingTalkError):
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        super().__init__(json_dump(payload))


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def default_helper_path() -> Path:
    return script_dir() / "cli.py"


CONFIG_PATH = Path(os.environ.get("DINGTALK_CONFIG", str(Path.home() / ".dingtalk-skills" / "config"))).expanduser()
SENSITIVE_CONFIG_KEYS = {
    "DINGTALK_ACCESS_TOKEN",
    "DINGTALK_APP_KEY",
    "DINGTALK_APP_SECRET",
    "DINGTALK_MY_OPERATOR_ID",
    "DINGTALK_MY_USER_ID",
    "DINGTALK_OLD_TOKEN",
}


def workspace_root() -> Path:
    override = os.environ.get("DINGTALK_WORKSPACE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path.cwd().resolve()


def default_cache_path() -> Path:
    return Path.home() / ".dingtalk-skills" / "dingtalk-knowledge-search" / "cache.sqlite"


def default_state_dir() -> Path:
    return Path.home() / ".dingtalk-skills" / "dingtalk-knowledge-search"


def default_assets_dir() -> Path:
    return Path.home() / ".dingtalk-skills" / "dingtalk-knowledge-search" / "assets"


def default_output_dir() -> Path:
    return workspace_root() / ".skills-workspace" / "dingtalk-knowledge-search" / "outputs"


def default_output_cache_dir() -> Path:
    return default_state_dir() / "output-cache"


def default_browser_state_path() -> Path:
    return default_state_dir() / "dingtalk-browser-state.json"


def default_browser_session() -> str:
    return "dingtalk-knowledge-search"


def default_browser_session_limit() -> int:
    return 10


def browser_session_registry_path() -> Path:
    return default_state_dir() / "browser-sessions.json"


def browser_session_lock_path() -> Path:
    return default_state_dir() / "browser-sessions.lock"


def default_browser_wait_ms() -> int:
    return 5000


def config_read() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def config_write(values: dict[str, str]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + ("\n" if values else ""), encoding="utf-8")


def config_get_value(key: str) -> str:
    return config_read().get(key, "")


def config_set_value(key: str, value: str) -> None:
    values = config_read()
    values[key] = value
    config_write(values)


def config_del_value(key: str) -> None:
    values = config_read()
    values.pop(key, None)
    config_write(values)


def config_require(key: str) -> str:
    value = config_get_value(key)
    if not value:
        raise DingTalkError(f"missing config {key}; set it with: cli.py config set {key}=<value>")
    return value


def config_mask(key: str, value: str) -> str:
    return f"{value[:6]}***" if key in SENSITIVE_CONFIG_KEYS and value else value


def helper_http_json(method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = resp.read().decode("utf-8")
    return json.loads(payload) if payload.strip() else {}


def helper_token(nocache: bool = False) -> str:
    app_key = config_require("DINGTALK_APP_KEY")
    app_secret = config_require("DINGTALK_APP_SECRET")
    now = int(time.time())
    if not nocache:
        cached = config_get_value("DINGTALK_ACCESS_TOKEN")
        expiry = int(config_get_value("DINGTALK_TOKEN_EXPIRY") or "0")
        if cached and now < expiry:
            return cached
    payload = helper_http_json("POST", f"{API_BASE}/v1.0/oauth2/accessToken", {"appKey": app_key, "appSecret": app_secret})
    token = str(payload.get("accessToken") or "")
    expire_in = int(payload.get("expireIn") or 0)
    if not token:
        raise DingTalkError(f"failed to get access token: {payload}")
    config_set_value("DINGTALK_ACCESS_TOKEN", token)
    config_set_value("DINGTALK_TOKEN_EXPIRY", str(now + expire_in - 200))
    return token


def helper_old_token(nocache: bool = False) -> str:
    app_key = config_require("DINGTALK_APP_KEY")
    app_secret = config_require("DINGTALK_APP_SECRET")
    now = int(time.time())
    if not nocache:
        cached = config_get_value("DINGTALK_OLD_TOKEN")
        expiry = int(config_get_value("DINGTALK_OLD_TOKEN_EXPIRY") or "0")
        if cached and now < expiry:
            return cached
    url = "https://oapi.dingtalk.com/gettoken?" + urllib.parse.urlencode({"appkey": app_key, "appsecret": app_secret})
    payload = helper_http_json("GET", url)
    token = str(payload.get("access_token") or "")
    expire_in = int(payload.get("expires_in") or 0)
    if not token:
        raise DingTalkError(f"failed to get old access token: {payload}")
    config_set_value("DINGTALK_OLD_TOKEN", token)
    config_set_value("DINGTALK_OLD_TOKEN_EXPIRY", str(now + expire_in - 200))
    return token


def helper_to_unionid(user_id: str | None = None) -> str:
    is_self = not user_id
    if not user_id:
        user_id = config_require("DINGTALK_MY_USER_ID")
    old_token = helper_old_token()
    url = "https://oapi.dingtalk.com/topapi/v2/user/get?" + urllib.parse.urlencode({"access_token": old_token})
    payload = helper_http_json("POST", url, {"userid": user_id})
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    union_id = str(result.get("unionid") or payload.get("unionid") or "")
    if not union_id:
        raise DingTalkError(f"userId to unionId conversion failed: {payload}")
    if is_self and not config_get_value("DINGTALK_MY_OPERATOR_ID"):
        config_set_value("DINGTALK_MY_OPERATOR_ID", union_id)
    return union_id


def run_helper(_helper: Path, *args: str) -> str:
    if not args:
        raise DingTalkError("helper command is empty")
    command = args[0]
    if command == "--get":
        lines = []
        for key in args[1:]:
            value = config_get_value(key)
            lines.append(f"{key}={value if value else '（未设置）'}")
        return "\n".join(lines)
    if command == "--set" and len(args) >= 2:
        if "=" not in args[1]:
            raise DingTalkError("config set requires KEY=VALUE")
        key, value = args[1].split("=", 1)
        config_set_value(key, value)
        return f"set {key}"
    if command == "--token":
        return helper_token("--nocache" in args[1:])
    if command == "--to-unionid":
        return helper_to_unionid(args[1] if len(args) > 1 else None)
    raise DingTalkError(f"unknown helper command: {' '.join(args)}")


PROXY_ALLOWED_HOSTS = {"alidocs.dingtalk.com", "static.dingtalk.com", "img.alicdn.com", "alidocs2-zjk-cdn.dingtalk.com"}
DEFAULT_PROXY_LINK_RETENTION_DAYS = 30
PROXY_LAST_CLEANUP_AT = 0.0


def proxy_config_path() -> Path:
    return default_state_dir() / "proxy.json"


def proxy_legacy_links_path() -> Path:
    return default_state_dir() / "proxy-links.json"


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def pick_port(preferred: int) -> int:
    for port in range(preferred, preferred + 100):
        if port_available(port):
            return port
    raise DingTalkError("no available port found")


def proxy_read_config() -> dict[str, object]:
    path = proxy_config_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def proxy_write_config(data: dict[str, object]) -> None:
    default_state_dir().mkdir(parents=True, exist_ok=True)
    proxy_config_path().write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def proxy_db_conn() -> sqlite3.Connection:
    default_state_dir().mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(default_cache_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS proxy_links (
            short_id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            last_access INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def proxy_migrate_json_links() -> int:
    path = proxy_legacy_links_path()
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    now = int(time.time())
    migrated = 0
    with proxy_db_conn() as conn:
        for key, value in payload.items():
            short_id = str(key)
            if isinstance(value, str):
                url = value
                created_at = now
                last_access = now
            elif isinstance(value, dict):
                url = str(value.get("url") or "")
                created_at = int(value.get("createdAt") or now)
                last_access = int(value.get("lastAccess") or created_at)
            else:
                continue
            if not url:
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO proxy_links (short_id, url, created_at, last_access)
                VALUES (?, ?, ?, ?)
                """,
                (short_id, url, created_at, last_access),
            )
            migrated += 1
    if migrated:
        with contextlib.suppress(OSError):
            path.rename(path.with_suffix(".json.migrated"))
    return migrated


def proxy_short_id_for_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def proxy_short_link_asset_dir(short_id: str) -> Path:
    return default_assets_dir() / "short-links" / short_id


def cleanup_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*"), reverse=True):
        try:
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        except OSError:
            continue


def proxy_cleanup_stale_links(retention_days: int = DEFAULT_PROXY_LINK_RETENTION_DAYS) -> dict[str, object]:
    if retention_days <= 0:
        return {"removedLinks": 0, "removedFiles": 0, "retentionDays": retention_days}
    cutoff = int(time.time()) - retention_days * 86400
    with proxy_db_conn() as conn:
        rows = conn.execute("SELECT short_id FROM proxy_links WHERE last_access < ?", (cutoff,)).fetchall()
        stale_ids = [str(row[0]) for row in rows]
        if stale_ids:
            conn.executemany("DELETE FROM proxy_links WHERE short_id = ?", [(short_id,) for short_id in stale_ids])
    removed_files = 0
    for short_id in stale_ids:
        asset_dir = proxy_short_link_asset_dir(short_id)
        if asset_dir.exists():
            for path in asset_dir.rglob("*"):
                if path.is_file():
                    removed_files += 1
            shutil.rmtree(asset_dir, ignore_errors=True)
    if stale_ids:
        cleanup_empty_dirs(default_assets_dir() / "short-links")
    return {"removedLinks": len(stale_ids), "removedFiles": removed_files, "retentionDays": retention_days}


def proxy_cleanup_stale_links_periodically(retention_days: int = DEFAULT_PROXY_LINK_RETENTION_DAYS) -> None:
    global PROXY_LAST_CLEANUP_AT
    now = time.time()
    if now - PROXY_LAST_CLEANUP_AT < 3600:
        return
    PROXY_LAST_CLEANUP_AT = now
    proxy_cleanup_stale_links(retention_days)


def proxy_touch_link(short_id: str) -> str:
    with proxy_db_conn() as conn:
        row = conn.execute("SELECT url FROM proxy_links WHERE short_id = ?", (short_id,)).fetchone()
        if not row:
            return ""
        conn.execute("UPDATE proxy_links SET last_access = ? WHERE short_id = ?", (int(time.time()), short_id))
        return str(row[0])


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def proxy_cookie_header_from_browser_state(state_path: Path, url: str) -> str:
    if not state_path.exists():
        return ""
    state = json.loads(state_path.read_text(encoding="utf-8"))
    cookies = state.get("cookies") if isinstance(state, dict) else []
    host = urllib.parse.urlparse(url).hostname or ""
    pairs: list[str] = []
    if not isinstance(cookies, list):
        return ""
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "")
        domain = str(cookie.get("domain") or "").lstrip(".")
        if name and domain and (host == domain or host.endswith("." + domain)):
            pairs.append(f"{name}={value}")
    return "; ".join(pairs)


def proxy_refresh_browser_state(state_path: Path) -> None:
    if not shutil.which("agent-browser"):
        return
    try:
        subprocess.run(["agent-browser", "--session", "dingtalk-knowledge-proxy-refresh", "--state", str(state_path), "open", "https://alidocs.dingtalk.com/"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        subprocess.run(["agent-browser", "--session", "dingtalk-knowledge-proxy-refresh", "wait", "5000"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        subprocess.run(["agent-browser", "--session", "dingtalk-knowledge-proxy-refresh", "state", "save", str(state_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except Exception:
        return


class ProxyHandler(BaseHTTPRequestHandler):
    browser_state: Path

    def do_GET(self) -> None:
        proxy_cleanup_stale_links_periodically()
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/r/"):
            short_id = parsed.path.split("/", 2)[-1]
            target = proxy_touch_link(short_id)
            if not target:
                self.send_error(404, "short link not found")
                return
            self.proxy_remote_image(target)
            return
        if parsed.path == "/local":
            params = urllib.parse.parse_qs(parsed.query)
            self.serve_local_asset(params.get("path", [""])[0])
            return
        if parsed.path.startswith("/local/"):
            self.serve_local_asset(urllib.parse.unquote(parsed.path[len("/local/"):]))
            return
        if parsed.path not in {"/image", "/resource"}:
            self.send_error(404)
            return
        params = urllib.parse.parse_qs(parsed.query)
        self.proxy_remote_image(params.get("url", [""])[0])

    def proxy_remote_image(self, target: str) -> None:
        target_url = urllib.parse.urlparse(target)
        if target_url.scheme != "https" or target_url.hostname not in PROXY_ALLOWED_HOSTS:
            self.send_error(403, "target host is not allowed")
            return
        headers = {
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://alidocs.dingtalk.com/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }
        cookie = proxy_cookie_header_from_browser_state(self.browser_state, target)
        if cookie:
            headers["Cookie"] = cookie
        try:
            req = urllib.request.Request(target, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
                content_type = response.headers.get("content-type", "application/octet-stream")
        except urllib.error.HTTPError as exc:
            if exc.code not in {401, 403}:
                self.send_error(exc.code, exc.reason)
                return
            proxy_refresh_browser_state(self.browser_state)
            cookie = proxy_cookie_header_from_browser_state(self.browser_state, target)
            if cookie:
                headers["Cookie"] = cookie
            try:
                req = urllib.request.Request(target, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as response:
                    data = response.read()
                    content_type = response.headers.get("content-type", "application/octet-stream")
            except urllib.error.HTTPError as retry_exc:
                self.send_error(retry_exc.code, retry_exc.reason)
                return
        self.send_image(data, content_type)

    def send_image(self, data: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "private, max-age=3600")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_local_asset(self, rel_path: str) -> None:
        root = default_assets_dir().resolve()
        target = (root / rel_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            self.send_error(403, "local path is outside assets root")
            return
        if not target.is_file():
            self.send_error(404, "local asset not found")
            return
        data = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_image(data, content_type)

    def log_message(self, format: str, *args: object) -> None:
        return


def proxy_serve(port: int, browser_state: Path) -> None:
    ProxyHandler.browser_state = browser_state
    server = ThreadingHTTPServer(("127.0.0.1", port), ProxyHandler)
    server.serve_forever()


def cmd_proxy_start(args: argparse.Namespace) -> int:
    config = proxy_read_config()
    current_pid = int(config.get("pid") or 0)
    if current_pid and process_alive(current_pid):
        os.kill(current_pid, signal.SIGTERM)
        time.sleep(0.5)
    preferred = int(config.get("port") or args.port)
    port = preferred if port_available(preferred) else pick_port(preferred + 1)
    browser_state = Path(args.browser_state).expanduser().resolve()
    default_state_dir().mkdir(parents=True, exist_ok=True)
    log_path = default_state_dir() / "proxy.log"
    with log_path.open("ab") as log_file:
        process = subprocess.Popen(
            [sys.executable, __file__, "proxy", "serve", "--port", str(port), "--browser-state", str(browser_state)],
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )
    data = {"pid": process.pid, "port": port, "browserState": str(browser_state), "startedAt": int(time.time()), "log": str(log_path)}
    proxy_write_config(data)
    print(json_dump({"status": "started", **data}))
    return 0


def cmd_proxy_status(_: argparse.Namespace) -> int:
    config = proxy_read_config()
    pid = int(config.get("pid") or 0)
    print(json_dump({**config, "running": bool(pid and process_alive(pid))}))
    return 0


def cmd_proxy_stop(_: argparse.Namespace) -> int:
    config = proxy_read_config()
    pid = int(config.get("pid") or 0)
    if pid and process_alive(pid):
        os.kill(pid, signal.SIGTERM)
    config["stoppedAt"] = int(time.time())
    proxy_write_config(config)
    print(json_dump({"status": "stopped", "pid": pid}))
    return 0


def cmd_proxy_shorten(args: argparse.Namespace) -> int:
    config = proxy_read_config()
    port = int(config.get("port") or args.port)
    short_id = proxy_short_id_for_url(args.url)
    now = int(time.time())
    with proxy_db_conn() as conn:
        conn.execute(
            """
            INSERT INTO proxy_links (short_id, url, created_at, last_access)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(short_id) DO UPDATE SET url = excluded.url, last_access = excluded.last_access
            """,
            (short_id, args.url, now, now),
        )
    print(json_dump({"id": short_id, "url": args.url, "proxyUrl": f"http://127.0.0.1:{port}/r/{short_id}"}))
    return 0


def cmd_proxy_cleanup(args: argparse.Namespace) -> int:
    print(json_dump(proxy_cleanup_stale_links(args.retention_days)))
    return 0


def build_proxy_parser(prog: str = "cli.py proxy") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="Local DingTalk resource proxy for Markdown previews.")
    sub = parser.add_subparsers(dest="proxy_command", required=True)
    start = sub.add_parser("start", help="Start or restart the local resource proxy")
    start.add_argument("--port", type=int, default=9697)
    start.add_argument("--browser-state", default=str(default_browser_state_path()))
    sub.add_parser("status", help="Show proxy status")
    sub.add_parser("stop", help="Stop the proxy")
    shorten = sub.add_parser("shorten", help="Create a proxy short link for a DingTalk resource URL")
    shorten.add_argument("url")
    shorten.add_argument("--port", type=int, default=9697)
    cleanup = sub.add_parser("cleanup", help="Remove stale proxy short links")
    cleanup.add_argument("--retention-days", type=int, default=DEFAULT_PROXY_LINK_RETENTION_DAYS)
    return parser


def helper_get_config(helper: Path, key: str) -> str:
    raw = run_helper(helper, "--get", key)
    value = raw.split("=", 1)[-1].strip() if "=" in raw else raw.strip()
    if value.startswith("（未设置"):
        return ""
    return value


def mask_secret(value: str) -> str:
    if not value:
        return ""
    return value[:4] + "****"


class DingTalkAuth:
    def __init__(self, helper: Path) -> None:
        self.helper: Path = helper
        self._token: str | None = None
        self._operator_id: str | None = None

    def operator_id(self) -> str:
        if self._operator_id:
            return self._operator_id
        raw = run_helper(self.helper, "--get", "DINGTALK_MY_OPERATOR_ID")
        value = raw.split("=", 1)[-1].strip() if "=" in raw else raw.strip()
        if not value or value.startswith("（未设置"):
            value = run_helper(self.helper, "--to-unionid").splitlines()[-1].strip()
        if not value:
            raise DingTalkError("DINGTALK_MY_OPERATOR_ID is empty after config lookup")
        self._operator_id = value
        return value

    def token(self, nocache: bool = False) -> str:
        if self._token and not nocache:
            return self._token
        args = ["--token"]
        if nocache:
            args.append("--nocache")
        self._token = run_helper(self.helper, *args)
        if not self._token:
            raise DingTalkError("empty access token from config")
        return self._token


class DingTalkClient:
    def __init__(self, auth: DingTalkAuth, sleep_seconds: float = 0.0) -> None:
        self.auth: DingTalkAuth = auth
        self.sleep_seconds: float = sleep_seconds

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
        retry: bool = True,
        add_operator_id: bool = True,
        attempt: int = 0,
    ) -> dict[str, object]:
        query_params = dict(params or {})
        if add_operator_id:
            query_params.setdefault("operatorId", self.auth.operator_id())
        query = urllib.parse.urlencode({key: value for key, value in query_params.items() if value is not None})
        url = f"{API_BASE}{path}"
        if query:
            url = f"{url}?{query}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        headers = {
            "x-acs-dingtalk-access-token": self.auth.token(),
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        if self.sleep_seconds:
            time.sleep(self.sleep_seconds)
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if retry and exc.code == 401:
                self.auth.token(nocache=True)
                return self.request(method, path, params=params, body=body, retry=False, add_operator_id=add_operator_id, attempt=attempt + 1)
            if retry and exc.code in {429, 502, 503, 504} and attempt < 4:
                time.sleep(min(2 ** attempt, 8))
                return self.request(method, path, params=params, body=body, retry=retry, add_operator_id=add_operator_id, attempt=attempt + 1)
            error_body = exc.read().decode("utf-8", errors="replace")
            raise DingTalkError(f"HTTP {exc.code} {method} {path}: {error_body}") from exc
        if not payload.strip():
            return {}
        parsed = json.loads(payload)
        return cast(dict[str, object], parsed) if isinstance(parsed, dict) else {"data": parsed}

    def search_dentries(self, keyword: str, limit: int = 10) -> dict[str, object]:
        max_results = max(1, min(limit, 50))
        return self.request(
            "POST",
            "/v2.0/storage/dentries/search",
            body={"keyword": keyword, "option": {"maxResults": max_results}},
        )

    def get_node(self, node_id: str) -> dict[str, object]:
        payload = self.request("GET", f"/v2.0/wiki/nodes/{urllib.parse.quote(node_id)}")
        node = payload.get("node")
        return cast(dict[str, object], node) if isinstance(node, dict) else payload

    def query_node_by_url(self, url: str) -> dict[str, object]:
        payload = self.request("POST", "/v2.0/wiki/nodes/queryByUrl", body={"url": url, "operatorId": self.auth.operator_id()})
        node = payload.get("node")
        return cast(dict[str, object], node) if isinstance(node, dict) else payload

    def read_blocks(self, doc_id: str) -> dict[str, object]:
        return self.request("GET", f"/v1.0/doc/suites/documents/{urllib.parse.quote(doc_id)}/blocks")

    def query_dentry_id_by_uuid(self, dentry_uuid: str) -> dict[str, object]:
        return self.request("GET", f"/v2.0/doc/dentries/{urllib.parse.quote(dentry_uuid)}/queryDentryId")

    def file_download_info(self, space_id: str, dentry_id: str) -> dict[str, object]:
        return self.request(
            "POST",
            f"/v1.0/storage/spaces/{urllib.parse.quote(space_id)}/dentries/{urllib.parse.quote(dentry_id)}/downloadInfos/query",
            params={"unionId": self.auth.operator_id()},
            body={"option": {"version": 1, "preferIntranet": False}},
            add_operator_id=False,
        )

    def notable_sheets(self, base_id: str) -> dict[str, object]:
        return self.request("GET", f"/v1.0/notable/bases/{urllib.parse.quote(base_id)}/sheets")

    def notable_fields(self, base_id: str, sheet_id: str) -> dict[str, object]:
        return self.request("GET", f"/v1.0/notable/bases/{urllib.parse.quote(base_id)}/sheets/{urllib.parse.quote(sheet_id)}/fields")

    def notable_records(self, base_id: str, sheet_id: str, max_results: int = 100, next_token: str = "") -> dict[str, object]:
        body: dict[str, object] = {"maxResults": max(1, min(max_results, 100))}
        if next_token:
            body["nextToken"] = next_token
        return self.request("POST", f"/v1.0/notable/bases/{urllib.parse.quote(base_id)}/sheets/{urllib.parse.quote(sheet_id)}/records/list", body=body)

    def workbook_sheets(self, workbook_id: str) -> dict[str, object]:
        return self.request("GET", f"/v1.0/doc/workbooks/{urllib.parse.quote(workbook_id)}/sheets")

    def workbook_sheet(self, workbook_id: str, sheet_id: str) -> dict[str, object]:
        return self.request("GET", f"/v1.0/doc/workbooks/{urllib.parse.quote(workbook_id)}/sheets/{urllib.parse.quote(sheet_id)}")

    def workbook_range(self, workbook_id: str, sheet_id: str, range_address: str) -> dict[str, object]:
        return self.request("GET", f"/v1.0/doc/workbooks/{urllib.parse.quote(workbook_id)}/sheets/{urllib.parse.quote(sheet_id)}/ranges/{urllib.parse.quote(range_address, safe='')}")


class Cache:
    def __init__(self, path: Path, enabled: bool = True, ttl_seconds: int = 86400) -> None:
        self.path = path
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self._conn: sqlite3.Connection | None = None

    def conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                namespace TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                created_at REAL NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (namespace, cache_key)
            )
            """
        )
        self._conn.execute("DELETE FROM cache_entries WHERE namespace = ?", ("search",))
        self._conn.commit()
        return self._conn

    def key(self, value: object) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, namespace: str, value: object) -> dict[str, object] | None:
        return self.get_with_ttl(namespace, value, enforce_ttl=True)

    def get_with_ttl(self, namespace: str, value: object, enforce_ttl: bool = True) -> dict[str, object] | None:
        if not self.enabled:
            return None
        cache_key = self.key(value)
        row = self.conn().execute(
            "SELECT created_at, payload FROM cache_entries WHERE namespace = ? AND cache_key = ?",
            (namespace, cache_key),
        ).fetchone()
        if not row:
            return None
        created_at = float(row[0])
        if enforce_ttl and self.ttl_seconds > 0 and time.time() - created_at > self.ttl_seconds:
            self.conn().execute("DELETE FROM cache_entries WHERE namespace = ? AND cache_key = ?", (namespace, cache_key))
            self.conn().commit()
            return None
        payload = json.loads(str(row[1]))
        return cast(dict[str, object], payload) if isinstance(payload, dict) else {"data": payload}

    def set(self, namespace: str, value: object, payload: dict[str, object]) -> None:
        if not self.enabled:
            return
        self.conn().execute(
            """
            INSERT OR REPLACE INTO cache_entries (namespace, cache_key, created_at, payload)
            VALUES (?, ?, ?, ?)
            """,
            (namespace, self.key(value), time.time(), json.dumps(payload, ensure_ascii=False, sort_keys=True)),
        )
        self.conn().commit()

    def cached(self, namespace: str, value: object, fetcher: object) -> dict[str, object]:
        cached_payload = self.get(namespace, value)
        if cached_payload is not None:
            cached_payload = dict(cached_payload)
            cached_payload.setdefault("_cache", {"hit": True, "namespace": namespace})
            return cached_payload
        payload = cast(Any, fetcher)()
        if isinstance(payload, dict):
            self.set(namespace, value, cast(dict[str, object], payload))
            return cast(dict[str, object], payload)
        return {"data": payload}

    def get_persistent(self, namespace: str, value: object) -> dict[str, object] | None:
        return self.get_with_ttl(namespace, value, enforce_ttl=False)

    def stats(self) -> dict[str, object]:
        if not self.path.exists():
            return {"path": str(self.path), "entries": 0, "namespaces": {}}
        rows = self.conn().execute("SELECT namespace, COUNT(*) FROM cache_entries GROUP BY namespace ORDER BY namespace").fetchall()
        total = sum(int(row[1]) for row in rows)
        return {"path": str(self.path), "entries": total, "namespaces": {str(row[0]): int(row[1]) for row in rows}}

    def clear(self, namespace: str | None = None) -> int:
        connection = self.conn()
        if namespace:
            before = connection.total_changes
            connection.execute("DELETE FROM cache_entries WHERE namespace = ?", (namespace,))
            connection.commit()
            return connection.total_changes - before
        before = connection.total_changes
        connection.execute("DELETE FROM cache_entries")
        connection.commit()
        return connection.total_changes - before

    def output_paths(self) -> list[Path]:
        if not self.path.exists():
            return []
        rows = self.conn().execute("SELECT payload FROM cache_entries WHERE namespace = ?", ("output",)).fetchall()
        paths: list[Path] = []
        seen: set[Path] = set()
        for row in rows:
            try:
                payload = json.loads(str(row[0]))
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            raw_paths = [str(payload.get("cachePath") or payload.get("path") or "")]
            outputs = payload.get("outputs")
            if isinstance(outputs, list):
                raw_paths.extend(str(item) for item in outputs if item)
            for raw_path in raw_paths:
                if not raw_path:
                    continue
                path = Path(raw_path).expanduser().resolve()
                if path not in seen:
                    seen.add(path)
                    paths.append(path)
        return paths

    def find_search_item(self, dentry_id: str) -> dict[str, object] | None:
        if not dentry_id or not self.enabled:
            return None
        rows = self.conn().execute("SELECT payload FROM cache_entries WHERE namespace = ?", ("search",)).fetchall()
        for row in rows:
            try:
                payload = json.loads(str(row[0]))
            except json.JSONDecodeError:
                continue
            items = payload.get("items") if isinstance(payload, dict) else []
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                candidate_id = str(item.get("dentryUuid") or item.get("nodeId") or item.get("dentryId") or "")
                if candidate_id == dentry_id:
                    return cast(dict[str, object], item)
        return None


def json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def block_list(blocks_payload: dict[str, object]) -> list[dict[str, object]]:
    result = blocks_payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("data"), list):
        return [item for item in result["data"] if isinstance(item, dict)]
    data = blocks_payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def block_text(block: dict[str, object], key: str) -> str:
    value = block.get(key)
    if isinstance(value, dict):
        for text_key in ("text", "content", "value"):
            text = value.get(text_key)
            if isinstance(text, str):
                return text
        return compact_json(value)
    return value if isinstance(value, str) else ""


def table_to_markdown(cells: object) -> list[str]:
    if not isinstance(cells, list):
        return []
    rows = [[str(cell).replace("\n", "<br>") for cell in row] for row in cells if isinstance(row, list)]
    if not rows:
        return []
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(padded[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for row in padded[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def render_attachment(block: dict[str, object]) -> list[str]:
    attachment = block.get("attachment")
    if not isinstance(attachment, dict):
        return ["<!-- attachment block without attachment payload -->", ""]
    name = str(attachment.get("name") or "untitled")
    resource_id = str(attachment.get("resourceId") or "")
    file_type = str(attachment.get("type") or "")
    view_type = str(attachment.get("viewType") or "")
    size = attachment.get("size")
    details = []
    if file_type:
        details.append(f"type={file_type}")
    if view_type:
        details.append(f"viewType={view_type}")
    if size not in (None, ""):
        details.append(f"size={size}")
    if resource_id:
        details.append(f"resourceId={resource_id}")
    suffix = f" ({', '.join(details)})" if details else ""
    return [f"[Attachment: {name}{suffix}]", ""]


def blocks_to_markdown(title: str, blocks_payload: dict[str, object]) -> str:
    lines = [f"# {title}", ""]
    for block in block_list(blocks_payload):
        block_type = block.get("blockType")
        if block_type == "heading":
            heading = block.get("heading") if isinstance(block.get("heading"), dict) else {}
            raw_level = str(cast(dict[str, object], heading).get("level", "heading-2"))
            match = re.search(r"(\d+)", raw_level)
            level = min(max(int(match.group(1)) if match else 2, 1), 6)
            text = str(cast(dict[str, object], heading).get("text", "")).strip()
            if text:
                lines.extend(["#" * level + " " + text, ""])
        elif block_type == "paragraph":
            text = block_text(block, "paragraph").strip()
            if text:
                lines.extend([text, ""])
        elif block_type == "unorderedList":
            text = block_text(block, "unorderedList").strip()
            if text:
                lines.append(f"- {text}")
        elif block_type == "orderedList":
            text = block_text(block, "orderedList").strip()
            if text:
                lines.append(f"1. {text}")
        elif block_type == "blockquote":
            text = block_text(block, "blockquote").strip()
            if text:
                lines.extend([f"> {text}", ""])
        elif block_type == "table":
            table = block.get("table") if isinstance(block.get("table"), dict) else {}
            table_lines = table_to_markdown(cast(dict[str, object], table).get("cells"))
            if table_lines:
                lines.extend(table_lines + [""])
        elif block_type == "attachment":
            lines.extend(render_attachment(block))
        elif block_type:
            lines.extend([f"<!-- Unsupported blockType: {block_type} -->", "```json", compact_json(block), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def blocks_to_markdown_with_images(title: str, blocks_payload: dict[str, object], image_refs: list[str]) -> str:
    lines = [f"# {title}", ""]
    image_index = 0
    for block in block_list(blocks_payload):
        block_type = block.get("blockType")
        if block_type == "heading":
            heading = block.get("heading") if isinstance(block.get("heading"), dict) else {}
            raw_level = str(cast(dict[str, object], heading).get("level", "heading-2"))
            match = re.search(r"(\d+)", raw_level)
            level = min(max(int(match.group(1)) if match else 2, 1), 6)
            text = str(cast(dict[str, object], heading).get("text", "")).strip()
            if text:
                lines.extend(["#" * level + " " + text, ""])
        elif block_type == "paragraph":
            text = block_text(block, "paragraph").strip()
            if text:
                lines.extend([text, ""])
        elif block_type == "unorderedList":
            text = block_text(block, "unorderedList").strip()
            if text:
                lines.append(f"- {text}")
        elif block_type == "orderedList":
            text = block_text(block, "orderedList").strip()
            if text:
                lines.append(f"1. {text}")
        elif block_type == "blockquote":
            text = block_text(block, "blockquote").strip()
            if text:
                lines.extend([f"> {text}", ""])
        elif block_type == "table":
            table = block.get("table") if isinstance(block.get("table"), dict) else {}
            table_lines = table_to_markdown(cast(dict[str, object], table).get("cells"))
            if table_lines:
                lines.extend(table_lines + [""])
        elif block_type == "attachment":
            lines.extend(render_attachment(block))
        elif block_type == "unknown":
            block_id = str(block.get("id") or "")
            if image_index < len(image_refs):
                image_index += 1
                lines.extend([f"![DingTalk image {image_index}]({image_refs[image_index - 1]})", ""])
            else:
                lines.extend([f"[Unsupported DingTalk rich block: blockId={block_id}, index={block.get('index')}]", ""])
        elif block_type:
            lines.extend([f"<!-- Unsupported blockType: {block_type} -->", "```json", compact_json(block), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def blocks_to_text(blocks_payload: dict[str, object]) -> str:
    lines: list[str] = []
    for block in block_list(blocks_payload):
        block_type = block.get("blockType")
        if block_type == "heading":
            heading = block.get("heading") if isinstance(block.get("heading"), dict) else {}
            text = str(cast(dict[str, object], heading).get("text", "")).strip()
        elif block_type in {"paragraph", "unorderedList", "orderedList", "blockquote"}:
            text = block_text(block, str(block_type)).strip()
        else:
            text = ""
        if text:
            lines.append(text)
    return "\n".join(lines).rstrip() + "\n"


def extract_tables(blocks_payload: dict[str, object]) -> list[dict[str, object]]:
    tables: list[dict[str, object]] = []
    for block in block_list(blocks_payload):
        if block.get("blockType") != "table" or not isinstance(block.get("table"), dict):
            continue
        table = cast(dict[str, object], block["table"])
        tables.append(
            {
                "blockId": block.get("id"),
                "index": block.get("index"),
                "colSize": table.get("colSize"),
                "rowSize": table.get("rowSize"),
                "cells": table.get("cells") or [],
                "markdown": "\n".join(table_to_markdown(table.get("cells"))),
            }
        )
    return tables


def extract_image_like_blocks(blocks_payload: dict[str, object]) -> list[dict[str, object]]:
    images = find_assets(blocks_payload)
    for block in block_list(blocks_payload):
        if block.get("blockType") == "unknown":
            images.append(
                {
                    "kind": "unknown",
                    "blockId": block.get("id"),
                    "index": block.get("index"),
                    "note": "DingTalk blocks API did not expose this rich block. It may be an image, diagram, TOC, embed, or other unsupported content.",
                }
            )
    return images


def run_agent_browser(args: list[str], parse_json: bool = False, timeout: int = 120) -> object:
    if not shutil.which("agent-browser"):
        raise DingTalkError('agent-browser is required. Install it with: npx skills add https://github.com/vercel-labs/agent-browser --skill agent-browser')
    env = os.environ.copy()
    browser_args = [arg.strip() for arg in env.get("AGENT_BROWSER_ARGS", "").split(",") if arg.strip()]
    for arg in ("--disable-gpu", "--disable-dev-shm-usage"):
        if arg not in browser_args:
            browser_args.append(arg)
    env["AGENT_BROWSER_ARGS"] = ",".join(browser_args)
    try:
        completed = subprocess.run(
            ["agent-browser", *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise DingTalkError(f"agent-browser failed for {' '.join(args[:3])}: {message}") from exc
    except subprocess.TimeoutExpired as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip() if isinstance(exc.stderr or exc.stdout, str) else str(exc)
        raise DingTalkError(f"agent-browser timed out for {' '.join(args[:3])}: {message}") from exc
    if not parse_json:
        return completed.stdout
    text = completed.stdout.strip()
    start = text.find("{")
    if start < 0:
        raise DingTalkError(f"agent-browser did not return JSON: {text[:300]}")
    payload = json.loads(text[start:])
    if isinstance(payload, dict) and payload.get("success") is False:
        raise DingTalkError(f"agent-browser failed: {payload}")
    return payload


def open_agent_browser_for_login(open_args: list[str], url: str) -> None:
    try:
        run_agent_browser([*open_args, "open", url], timeout=120)
    except DingTalkError as exc:
        # DingTalk login pages can keep loading while waiting for QR scan or
        # confirmation. Keep polling the page state instead of aborting early.
        text = str(exc).lower()
        if "timed out" not in text and "operation timed out" not in text:
            raise


def close_agent_browser_force() -> list[str]:
    try:
        run_agent_browser(["close", "--all"], timeout=120)
    except DingTalkError:
        try:
            run_agent_browser(["close"], timeout=120)
        except DingTalkError:
            pass
    patterns = [
        "agent-browser-linux-x64",
        "/tmp/agent-browser-chrome-",
    ]
    for pattern in patterns:
        subprocess.run(["pkill", "-f", pattern], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
    wait_for_agent_browser_processes(patterns, timeout_seconds=15)
    for pattern in patterns:
        if process_pattern_running(pattern):
            subprocess.run(["pkill", "-9", "-f", pattern], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
    wait_for_agent_browser_processes(patterns, timeout_seconds=10)
    remaining: list[str] = []
    for pattern in patterns:
        remaining.extend(process_pattern_lines(pattern))
    return sorted(set(remaining))


def process_pattern_running(pattern: str) -> bool:
    try:
        completed = subprocess.run(["pgrep", "-f", pattern], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
    except subprocess.TimeoutExpired:
        return True
    return completed.returncode == 0 and bool(completed.stdout.strip())


def process_pattern_lines(pattern: str) -> list[str]:
    try:
        completed = subprocess.run(["pgrep", "-af", pattern], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
    except subprocess.TimeoutExpired:
        return [f"<pgrep timed out for {pattern}>"]
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def wait_for_agent_browser_processes(patterns: list[str], timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not any(process_pattern_running(pattern) for pattern in patterns):
            return
        time.sleep(0.5)


@contextlib.contextmanager
def browser_session_slot(session: str, limit: int = default_browser_session_limit()):
    lock_path = browser_session_lock_path()
    registry_path = browser_session_registry_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        deadline = time.time() + 300
        acquired = False
        while time.time() < deadline:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                sessions = read_browser_session_registry(registry_path)
                now = time.time()
                sessions = {name: ts for name, ts in sessions.items() if now - ts < 900 and is_agent_browser_session_active(name)}
                if session in sessions or len(sessions) < limit:
                    sessions[session] = now
                    write_browser_session_registry(registry_path, sessions)
                    acquired = True
                    break
                write_browser_session_registry(registry_path, sessions)
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            time.sleep(1)
        if not acquired:
            raise DingTalkError(f"too many active agent-browser sessions; limit={limit}")
        try:
            yield
        finally:
            keep_open = os.environ.get("DINGTALK_KEEP_BROWSER_OPEN") in {"1", "true", "yes"} or (sys.exc_info()[0] is LoginRequired and session == default_browser_session())
            if not keep_open:
                with contextlib.suppress(DingTalkError):
                    run_agent_browser(["--session", session, "close"], timeout=120)
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                sessions = read_browser_session_registry(registry_path)
                sessions.pop(session, None)
                write_browser_session_registry(registry_path, sessions)
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)


def read_browser_session_registry(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): float(value) for key, value in raw.items() if isinstance(value, (int, float))}


def write_browser_session_registry(path: Path, sessions: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sessions, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def is_agent_browser_session_active(session: str) -> bool:
    try:
        completed = subprocess.run(["agent-browser", "session", "list", "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return True
    if completed.returncode != 0:
        return True
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return True
    text = json.dumps(payload, ensure_ascii=False)
    return session in text


def browser_session_for(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{default_browser_session()}-{digest}"


def login_qr_screenshot_path(session: str) -> Path:
    safe_session = re.sub(r"[^A-Za-z0-9_.-]+", "-", session).strip("-") or default_browser_session()
    default_dir = workspace_root() / ".skills-workspace" / "dingtalk-knowledge-search"
    screenshot_dir = Path(os.environ.get("DINGTALK_LOGIN_SCREENSHOT_DIR", str(default_dir))).expanduser().resolve()
    return screenshot_dir / f"{safe_session}-login-qr.png"


def capture_login_screenshot(session: str, screenshot_path: Path) -> Path:
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    selector = qr_screenshot_selector(session)
    if selector:
        with contextlib.suppress(DingTalkError):
            run_agent_browser(["--session", session, "screenshot", selector, str(screenshot_path)], timeout=120)
            return screenshot_path
    run_agent_browser(["--session", session, "screenshot", str(screenshot_path)], timeout=120)
    return screenshot_path


def qr_screenshot_selector(session: str) -> str:
    script = r'''
(() => {
  const visible = el => {
    if (!el) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== 'hidden' && style.display !== 'none' && rect.width >= 80 && rect.height >= 80;
  };
  const isReadyImage = img => visible(img) && img.complete && img.naturalWidth >= 80 && img.naturalHeight >= 80;
  const isReadyCanvas = canvas => visible(canvas) && canvas.width >= 80 && canvas.height >= 80;
  const isReadyBackground = el => visible(el) && /url\(/.test(getComputedStyle(el).backgroundImage || '');
  const candidates = [
    ...[...document.querySelectorAll('canvas')].filter(isReadyCanvas),
    ...[...document.querySelectorAll('img')].filter(isReadyImage),
    ...[...document.querySelectorAll('div, span')].filter(isReadyBackground),
  ];
  if (!candidates.length) return '';
  const qr = candidates
    .map(el => ({ el, rect: el.getBoundingClientRect() }))
    .filter(item => item.rect.width >= 80 && item.rect.height >= 80)
    .sort((a, b) => Math.abs((a.rect.width / a.rect.height) - 1) - Math.abs((b.rect.width / b.rect.height) - 1))[0]?.el;
  if (!qr) return '';
  qr.setAttribute('data-dingtalk-login-qr-capture', '1');
  return '[data-dingtalk-login-qr-capture="1"]';
})()
'''
    payload = cast(dict[str, object], run_agent_browser(["--session", session, "eval", script, "--json"], parse_json=True, timeout=120))
    data = payload.get("data")
    result = cast(dict[str, object], data).get("result") if isinstance(data, dict) else ""
    return str(result or "")


def wait_for_login_qr_rendered(session: str, timeout_seconds: int = 60) -> bool:
    script = r'''
(() => {
  const visible = el => {
    if (!el) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== 'hidden' && style.display !== 'none' && rect.width >= 80 && rect.height >= 80;
  };
  const clickableVisible = el => {
    if (!el) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
  };
  const bodyText = document.body ? document.body.innerText : '';
  const hasText = /Scan the code with DingDing|QR Code|扫码/.test(bodyText);
  const hasFailure = /QR Code failure|二维码失效|二维码已失效|刷新/.test(bodyText);
  const clickRefresh = () => {
    const candidates = [...document.querySelectorAll('button, [role="button"], a, div, span')].filter(clickableVisible);
    const refresh = candidates.find(el => /^(Refresh|刷新)$/.test((el.innerText || el.textContent || '').trim()));
    if (!refresh) return false;
    const r = refresh.getBoundingClientRect();
    for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
      refresh.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, view: window }));
    }
    return true;
  };
  if (hasFailure) {
    return { hasText, hasQr: false, hasFailure: true, refreshed: clickRefresh(), href: location.href, title: document.title };
  }
  const imageReady = img => visible(img) && img.complete && img.naturalWidth >= 80 && img.naturalHeight >= 80;
  const canvasReady = canvas => {
    if (!visible(canvas) || canvas.width < 80 || canvas.height < 80) return false;
    try {
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (!ctx) return true;
      const w = Math.min(canvas.width, 160);
      const h = Math.min(canvas.height, 160);
      const data = ctx.getImageData(0, 0, w, h).data;
      let dark = 0;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i] < 180 || data[i + 1] < 180 || data[i + 2] < 180) dark += 1;
      }
      return dark > 200;
    } catch (_) {
      return true;
    }
  };
  const bgReady = el => {
    if (!visible(el)) return false;
    const bg = getComputedStyle(el).backgroundImage;
    return bg && bg !== 'none' && /url\(/.test(bg);
  };
  const imgs = [...document.querySelectorAll('img')];
  const canvases = [...document.querySelectorAll('canvas')];
  const divs = [...document.querySelectorAll('div, span')];
  return {
    hasText,
    hasQr: imgs.some(imageReady) || canvases.some(canvasReady) || divs.some(bgReady),
    hasFailure,
    imageCount: imgs.length,
    canvasCount: canvases.length,
    href: location.href,
    title: document.title,
  };
})()
'''
    deadline = time.monotonic() + timeout_seconds
    refreshed_failure = False
    while time.monotonic() < deadline:
        payload = cast(dict[str, object], run_agent_browser(["--session", session, "eval", script, "--json"], parse_json=True, timeout=120))
        data = payload.get("data")
        result = cast(dict[str, object], data).get("result") if isinstance(data, dict) else {}
        if isinstance(result, dict):
            if is_alidocs_document_loaded({"href": result.get("href"), "iframeCount": 1 if str(result.get("href") or "").startswith("https://alidocs.dingtalk.com/") else 0}):
                return True
            if result.get("hasFailure"):
                refreshed_failure = bool(result.get("refreshed")) or refreshed_failure
                run_agent_browser(["--session", session, "wait", "2000"], timeout=120)
                continue
            if result.get("hasText") and result.get("hasQr"):
                return True
        run_agent_browser(["--session", session, "wait", "1000"], timeout=120)
    return False


def refresh_browser_state(
    state_path: Path,
    session: str,
    url: str = "https://alidocs.dingtalk.com/",
    emit: bool = True,
) -> bool:
    if not shutil.which("agent-browser"):
        raise DingTalkError(
            "agent-browser is required to refresh DingTalk browser state. "
            "Install it with: npx skills add https://github.com/vercel-labs/agent-browser --skill agent-browser"
        )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    active = is_agent_browser_session_active(session)
    if active:
        with contextlib.suppress(DingTalkError):
            state = current_browser_page_state(session)
            if str(state.get("href") or "") == "about:blank":
                active = False

    if active:
        result = save_browser_state_if_authenticated(state_path, session)
        if result["authenticated"]:
            if emit:
                print(json_dump({**result, "action": "authenticated"}))
            return True
        if not wait_for_login_qr_rendered(session):
            if emit:
                print(json_dump({**result, "action": "qr_not_ready", "message": "DingTalk login page opened, but the QR code image was not rendered yet. Retry login."}))
            return False
        screenshot_path = capture_login_screenshot(session, login_qr_screenshot_path(session))
        if emit:
            print(json_dump({**result, "action": "scan_required", "screenshotPath": str(screenshot_path)}))
        return False

    with contextlib.suppress(DingTalkError):
        run_agent_browser(["--session", session, "close"], timeout=120)

    open_args = ["--session", session]
    if state_path.exists():
        open_args.extend(["--state", str(state_path)])
    open_agent_browser_for_login(open_args, url)

    result = save_browser_state_if_authenticated(state_path, session)
    if result["authenticated"]:
        if emit:
            print(json_dump({**result, "action": "authenticated"}))
        return True

    if not wait_for_login_qr_rendered(session):
        if emit:
            print(json_dump({**result, "action": "qr_not_ready", "message": "DingTalk login page opened, but the QR code image was not rendered yet. Retry login."}))
        return False

    screenshot_path = capture_login_screenshot(session, login_qr_screenshot_path(session))
    if emit:
        print(json_dump({**result, "action": "scan_required", "screenshotPath": str(screenshot_path)}))
    return False


def login_required_payload(state_path: Path, session: str) -> dict[str, object]:
    state = current_browser_page_state(session)
    payload: dict[str, object] = {
        "loginRequired": True,
        "action": "scan_required",
        "message": "DingTalk login is required. Scan the QR screenshot, then rerun the command.",
        "href": str(state.get("href") or ""),
        "iframeCount": int(state.get("iframeCount") or 0),
        "statePath": str(state_path),
        "screenshotPath": str(login_qr_screenshot_path(session)),
    }
    return payload


def ensure_default_browser_state(state_path: Path, url: str, emit: bool = False) -> None:
    session = default_browser_session()
    if not refresh_browser_state(state_path, session, url, emit=emit):
        raise LoginRequired(login_required_payload(state_path, session))


def save_browser_state_if_authenticated(state_path: Path, session: str, close_after_save: bool = True) -> dict[str, object]:
    state = current_browser_page_state(session)
    authenticated = is_alidocs_document_loaded(state)
    if authenticated:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        run_agent_browser(["--session", session, "state", "save", str(state_path)], timeout=120)
        if close_after_save:
            with contextlib.suppress(DingTalkError):
                run_agent_browser(["--session", session, "close"], timeout=120)
    return {
        "authenticated": authenticated,
        "href": str(state.get("href") or ""),
        "iframeCount": int(state.get("iframeCount") or 0),
        "statePath": str(state_path),
    }


def current_browser_page_state(session: str) -> dict[str, object]:
    script = "(() => ({href: location.href, title: document.title, iframeCount: document.querySelectorAll('iframe').length, text: document.body ? document.body.innerText.slice(0, 1200) : ''}))()"
    payload = cast(dict[str, object], run_agent_browser(["--session", session, "eval", script, "--json"], parse_json=True, timeout=120))
    data = payload.get("data")
    result = cast(dict[str, object], data).get("result") if isinstance(data, dict) else {}
    return cast(dict[str, object], result if isinstance(result, dict) else {})


def is_alidocs_document_loaded(state: dict[str, object]) -> bool:
    href = str(state.get("href") or "")
    iframe_count = int(state.get("iframeCount") or 0)
    return href.startswith("https://alidocs.dingtalk.com/") and iframe_count > 0


def browser_state_has_dingtalk_doc_session(state_path: Path) -> bool:
    if not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    cookies = state.get("cookies") if isinstance(state, dict) else []
    if not isinstance(cookies, list):
        return False
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        domain = str(cookie.get("domain") or "")
        if name == "doc_atoken" and "dingtalk.com" in domain:
            return True
    return False


def extract_image_urls_from_browser(url: str, state_path: Path, session: str, wait_ms: int) -> list[str]:
    if not state_path.exists():
        ensure_default_browser_state(state_path, url, emit=False)
    run_agent_browser(["--session", session, "--state", str(state_path), "open", url], timeout=120)
    run_agent_browser(["--session", session, "wait", str(wait_ms)], timeout=120)
    run_agent_browser(["--session", session, "state", "save", str(state_path)], timeout=120)
    run_agent_browser(["--session", session, "network", "requests", "--json"], timeout=120)
    script = r"""
(() => {
  const urls = new Set();
  const add = value => {
    if (!value || typeof value !== 'string') return;
    if (value.startsWith('data:')) return;
    if (value.startsWith('http')) urls.add(value);
  };
  const collect = doc => {
    [...doc.querySelectorAll('img')].forEach(img => add(img.currentSrc || img.src));
    [...doc.querySelectorAll('*')].forEach(el => {
      const bg = getComputedStyle(el).backgroundImage;
      if (!bg || bg === 'none') return;
      [...bg.matchAll(/url\(["']?([^"')]+)["']?\)/g)].forEach(match => add(match[1]));
    });
  };
  collect(document);
  [...document.querySelectorAll('iframe')].forEach(frame => {
    try {
      const doc = frame.contentDocument || frame.contentWindow.document;
      if (doc) collect(doc);
    } catch (_) {}
  });
  return [...urls].filter(url => {
    const lower = url.toLowerCase();
    return lower.includes('/core/api/resources/img/') || lower.includes('alidocs2-zjk-cdn.dingtalk.com/res/') || /\.(png|jpe?g|webp|gif|svg)(\?|$)/.test(lower);
  });
})()
"""
    dom_payload = cast(dict[str, object], run_agent_browser(["--session", session, "eval", script, "--json"], parse_json=True, timeout=120))
    data = dom_payload.get("data")
    result = cast(dict[str, object], data).get("result") if isinstance(data, dict) else []
    urls = [str(item) for item in result] if isinstance(result, list) else []
    filtered: list[str] = []
    for item in urls:
        lower = item.lower()
        if any(skip in lower for skip in ["personal-center-avatar", "profile", "font", "emoji"]):
            continue
        if item not in filtered:
            filtered.append(item)
    return filtered


def extract_image_urls_with_session(url: str, state_path: Path, wait_ms: int) -> list[str]:
    session = browser_session_for(f"images:{url}")
    with browser_session_slot(session):
        return extract_image_urls_from_browser(url, state_path, session, wait_ms)


def private_markdown_with_session(url: str, state_path: Path, wait_ms: int, include_diagram: bool = False) -> str:
    session = browser_session_for(f"markdown:{url}:{include_diagram}")
    with browser_session_slot(session):
        return private_markdown_from_browser(url, state_path, session, wait_ms, include_diagram=include_diagram)


def cookie_header_from_browser_state(state_path: Path, url: str) -> str:
    if not state_path.exists():
        return ""
    state = json.loads(state_path.read_text(encoding="utf-8"))
    cookies = state.get("cookies") if isinstance(state, dict) else []
    host = urllib.parse.urlparse(url).hostname or ""
    pairs: list[str] = []
    if not isinstance(cookies, list):
        return ""
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "")
        domain = str(cookie.get("domain") or "").lstrip(".")
        if not name or not domain:
            continue
        if host == domain or host.endswith("." + domain):
            pairs.append(f"{name}={value}")
    return "; ".join(pairs)


def cookie_header_from_browser_state_for_domain(state_path: Path, domain_suffix: str) -> str:
    if not state_path.exists():
        return ""
    state = json.loads(state_path.read_text(encoding="utf-8"))
    cookies = state.get("cookies") if isinstance(state, dict) else []
    if not isinstance(cookies, list):
        return ""
    suffix = domain_suffix.lstrip(".")
    pairs: list[str] = []
    seen: set[str] = set()
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "")
        domain = str(cookie.get("domain") or "").lstrip(".")
        if not name or not domain or not value:
            continue
        if domain == suffix or domain.endswith("." + suffix):
            key = f"{name}={value}"
            if key not in seen:
                seen.add(key)
                pairs.append(key)
    return "; ".join(pairs)


def download_images(urls: list[str], assets_dir: Path, doc_id: str, state_path: Path | None = None) -> list[str]:
    doc_dir = assets_dir / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    local_refs: list[str] = []
    for index, url in enumerate(urls, start=1):
        parsed_path = urllib.parse.urlparse(url).path
        content_type = mimetypes.guess_type(parsed_path)[0]
        ext = mimetypes.guess_extension(content_type or "image/png") or ".png"
        filename = f"image-{index:03d}{ext}"
        output_path = doc_dir / filename
        if not output_path.exists():
            headers = {
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": "https://alidocs.dingtalk.com/",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            }
            if state_path:
                cookie_header = cookie_header_from_browser_state(state_path, url)
                if cookie_header:
                    headers["Cookie"] = cookie_header
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                content_type = response.headers.get("content-type", "")
                data = response.read()
                if "image" not in content_type.lower() and not data.startswith((b"\x89PNG", b"\xff\xd8", b"GIF8", b"RIFF")):
                    raise DingTalkError(f"downloaded non-image response for {url}: content-type={content_type}")
                output_path.write_bytes(data)
        local_refs.append(str(output_path))
    return local_refs


def cleanup_old_assets(assets_dir: Path, retention_days: int) -> int:
    if retention_days <= 0 or not assets_dir.exists():
        return 0
    cutoff = time.time() - retention_days * 86400
    removed = 0
    for path in sorted(assets_dir.rglob("*"), reverse=True):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        except OSError:
            continue
    return removed


def private_markdown_from_browser(
    url: str,
    state_path: Path,
    session: str,
    wait_ms: int,
    include_diagram: bool = False,
) -> str:
    """Render Markdown from DingTalk's web document payload.

    The official blocks API hides many images as `unknown`. The web app's
    /api/document/data payload contains the ordered body and real `img` nodes.
    """
    state_path.parent.mkdir(parents=True, exist_ok=True)
    script = r'''
(() => {
  const includeDiagram = __INCLUDE_DIAGRAM__;
  return (async () => {
  const frame = document.querySelector('iframe');
  const win = frame && frame.contentWindow;
  if (!win) return { error: 'no document iframe' };
  const frameUrl = new URL(frame.src);
  const dentryKey = frameUrl.searchParams.get('dentryKey');
  const resp = await win.fetch('/api/document/data', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'a-dentry-key': dentryKey },
    body: JSON.stringify({ fetchBody: true }),
    credentials: 'include'
  });
  const payload = await resp.json();
  const content = JSON.parse(payload.data.documentContent.checkpoint.content);
  const body = content.parts[content.main].data.body;
  const parts = content.parts || {};
  const title = payload.data.fileMetaInfo?.name || document.title || 'DingTalk document';
  const fullUrl = src => !src ? '' : src.startsWith('http') ? src : `https://alidocs.dingtalk.com${src}`;
  const textOf = value => {
    let out = '';
    const walk = v => {
      if (typeof v === 'string') out += v;
      else if (Array.isArray(v)) {
        if (v[0] === 'img' || v[0] === 'toc' || v[0] === 'card') return;
        v.slice(2).forEach(walk);
      }
    };
    walk(value);
    return out.replace(/\n+/g, '\n').trim();
  };
  const imagesOf = value => {
    const out = [];
    const walk = v => {
      if (Array.isArray(v)) {
        if (v[0] === 'img' && v[1]?.src) out.push(v[1]);
        v.forEach(walk);
      }
    };
    walk(value);
    return out;
  };
  const tableRows = table => table.slice(2).filter(r => Array.isArray(r) && r[0] === 'tr').map(row => row.slice(2).filter(c => Array.isArray(c) && c[0] === 'tc').map(c => textOf(c).replace(/\n/g, '<br>'))).filter(r => r.length);
  const tableMd = rows => {
    if (!rows.length) return '';
    const width = Math.max(...rows.map(r => r.length));
    const pad = r => [...r, ...Array(width - r.length).fill('')];
    const padded = rows.map(pad);
    return [`| ${padded[0].join(' | ')} |`, `| ${Array(width).fill('---').join(' | ')} |`, ...padded.slice(1).map(r => `| ${r.join(' | ')} |`)].join('\n');
  };
  const renderNodeMarkdown = node => {
    if (!Array.isArray(node)) return [];
    const tag = node[0];
    if (/^h[1-6]$/.test(tag)) {
      const text = textOf(node);
      return text ? [`${'#'.repeat(Number(tag.slice(1)))} ${text}`, ''] : [];
    }
    if (tag === 'p') {
      const text = textOf(node);
      const list = node[1]?.list;
      const lines = [];
      if (text) lines.push(list?.isOrdered ? `1. ${text}` : list ? `- ${text}` : text, '');
      for (const img of imagesOf(node)) lines.push(`![${img.name || 'image'}](${fullUrl(img.src)})`, '');
      return lines;
    }
    if (tag === 'table') {
      const md = tableMd(tableRows(node));
      return md ? [md, ''] : [];
    }
    if (tag === 'code') {
      const lang = String(node[1]?.language || node[1]?.lang || '').trim();
      const text = textOf(node);
      return text ? ['```' + lang, text, '```', ''] : [];
    }
    if (tag === 'pre') {
      const codeChild = node.slice(2).find(child => Array.isArray(child) && child[0] === 'code');
      const lang = String(codeChild?.[1]?.language || codeChild?.[1]?.lang || node[1]?.language || '').trim();
      const text = textOf(codeChild || node);
      return text ? ['```' + lang, text, '```', ''] : [];
    }
    if (tag === 'container') {
      const rows = node.slice(2).filter(child => Array.isArray(child) && child[0] === 'table').flatMap(tableRows).filter(row => row.length);
      if (rows.length) {
        const md = tableMd(rows);
        return md ? [md, ''] : [];
      }
      const lines = [];
      for (const child of node.slice(2)) lines.push(...renderNodeMarkdown(child));
      return lines;
    }
    if (tag === 'card') {
      const type = node[1]?.metadata?.type || 'card';
      const id = node[1]?.metadata?.id;
      const part = id && parts[id];
      const data = part && part.data;
      if (includeDiagram && type === 'application/x-alidocs-plugin-text-diagram' && data?.code) {
        const lang = detectDiagramLang(data.type, data.code);
        return ['```' + lang, data.code, '```', ''];
      }
      return [`[Unsupported DingTalk card: ${type}]`, ''];
    }
    return [];
  };
  const detectDiagramLang = (type, code) => {
    const declared = String(type || '').toLowerCase();
    const source = String(code || '').trim();
    const lower = source.toLowerCase();
    if (['mermaid', 'plantuml', 'dot', 'graphviz'].includes(declared)) return declared === 'graphviz' ? 'dot' : declared;
    if (/^@start\w+/i.test(source) || lower.includes('@enduml')) return 'plantuml';
    if (/^(flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|mindmap|timeline|gitGraph)\b/.test(source)) return 'mermaid';
    if (/^graph\s+(TD|TB|BT|RL|LR)\b/.test(source)) return 'mermaid';
    if (/^(di)?graph\s+\w*\s*\{/.test(source)) return 'dot';
    return declared || 'text';
  };
  const lines = [`# ${title}`, ''];
  for (const node of body.slice(2)) {
    lines.push(...renderNodeMarkdown(node));
  }
  return { markdown: lines.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n' };
  })();
})()
'''
    script = script.replace("__INCLUDE_DIAGRAM__", "true" if include_diagram else "false")
    last_error = "failed to get private document payload"
    for attempt in range(2):
        open_args = ["--session", session]
        if state_path.exists():
            open_args.extend(["--state", str(state_path)])
        try:
            open_agent_browser_for_login(open_args, url)
        except DingTalkError as exc:
            text = str(exc).lower()
            if any(token in text for token in ("login", "403", "401", "forbidden", "denied", "timeout", "timed out")):
                if not refresh_browser_state(state_path, default_browser_session(), url, emit=False):
                    raise LoginRequired(login_required_payload(state_path, default_browser_session()))
                continue
            raise
        run_agent_browser(["--session", session, "wait", str(wait_ms)], timeout=120)
        run_agent_browser(["--session", session, "state", "save", str(state_path)], timeout=120)
        payload = cast(dict[str, object], run_agent_browser(["--session", session, "eval", script, "--json"], parse_json=True, timeout=120))
        data = payload.get("data")
        result = cast(dict[str, object], data).get("result") if isinstance(data, dict) else None
        if isinstance(result, dict) and not result.get("error"):
            markdown = result.get("markdown")
            if isinstance(markdown, str):
                return markdown
            last_error = "private document payload did not return markdown"
        else:
            error_text = result.get("error") if isinstance(result, dict) else None
            last_error = str(error_text or f"failed to get private document payload: {payload}")
        if attempt == 0 and any(token in last_error.lower() for token in ("iframe", "login", "403", "401", "forbidden", "denied")):
            if not refresh_browser_state(state_path, default_browser_session(), url, emit=False):
                raise LoginRequired(login_required_payload(state_path, default_browser_session()))
            continue
        break
    if "no document iframe" in last_error.lower() and not browser_state_has_dingtalk_doc_session(state_path):
        ensure_default_browser_state(state_path, url, emit=False)
        return private_markdown_from_browser(url, state_path, session, wait_ms, include_diagram=include_diagram)
    raise DingTalkError(last_error)


def should_use_browser_fallback(error: DingTalkError) -> bool:
    text = str(error).lower()
    return "403" in text or "forbidden.accessdenied" in text or "the operator has no permission" in text


def should_download_as_file(error: DingTalkError) -> bool:
    text = str(error).lower()
    return "doc key is illegal" in text or "invalidrequest.inputargs.invalid" in text


def reject_folder_node(node: dict[str, object], node_id: str, title: str) -> None:
    if str(node.get("type") or "").upper() != "FOLDER":
        return
    raise DingTalkError(f"node {node_id} ({title}) is a folder and cannot be read directly; read a child document instead")


def cmd_login(args: argparse.Namespace) -> int:
    state_path = default_browser_state_path().expanduser().resolve()
    url = args.url_option or args.url
    completed = refresh_browser_state(
        state_path,
        default_browser_session(),
        url,
    )
    return 0 if completed else 2


def localize_markdown_images(markdown: str, assets_dir: Path, doc_id: str, state_path: Path) -> str:
    urls = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    local_paths = download_images(urls, assets_dir, doc_id, state_path=state_path)
    for url, local_path in zip(urls, local_paths):
        markdown = markdown.replace(f"({url})", f"({local_path})")
    return markdown


def proxify_markdown_images(markdown: str, port: int) -> str:
    urls = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    for url in urls:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        proxy_url = "http://127.0.0.1:" + str(port) + "/r/" + register_proxy_short_link(url)
        markdown = markdown.replace(f"({url})", f"({proxy_url})")
    return markdown


def register_proxy_short_link(url: str) -> str:
    short_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    now = int(time.time())
    cache_path = default_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(cache_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS proxy_links (
                short_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_access INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO proxy_links (short_id, url, created_at, last_access)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(short_id) DO UPDATE SET url = excluded.url, last_access = excluded.last_access
            """,
            (short_id, url, now, now),
        )
    return short_id


def resolve_image_refs(args: argparse.Namespace, doc_id: str) -> list[str]:
    requested = set(getattr(args, "with_parts", []) or [])
    if not requested.intersection({"img", "img-origin", "img-local"}):
        return []
    if not getattr(args, "source_url", None):
        raise DingTalkError("--with img/img-origin/img-local requires an alidocs URL or --source-url")
    state_path = default_browser_state_path().expanduser().resolve()
    urls = extract_image_urls_with_session(args.source_url, state_path, default_browser_wait_ms())
    if "img-local" in requested:
        return download_images(urls, Path(args.assets_dir).expanduser().resolve(), doc_id, state_path=state_path)
    return urls


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "-", value).strip(".-")
    return (cleaned or "dingtalk-document")[:120]


def filename_from_content_disposition(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"filename\*=([^']*)''([^;]+)", value, flags=re.IGNORECASE)
    if match:
        return urllib.parse.unquote(match.group(2).strip().strip('"'))
    match = re.search(r'filename="?([^";]+)"?', value, flags=re.IGNORECASE)
    if match:
        return urllib.parse.unquote(match.group(1).strip())
    return ""


def filename_from_download_response(title: str, extension: str, url: str, headers: object) -> tuple[str, str]:
    header_get = getattr(headers, "get", None)
    content_disposition = str(header_get("content-disposition", "") if callable(header_get) else "")
    response_name = filename_from_content_disposition(content_disposition)
    if not response_name:
        parsed_name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
        if parsed_name and "." in parsed_name:
            response_name = parsed_name
    filename = safe_filename(response_name or title)
    inferred_extension = extension.lower().lstrip(".")
    suffix = Path(filename).suffix.lstrip(".").lower()
    if suffix:
        inferred_extension = inferred_extension or suffix
        return filename, inferred_extension
    content_type = str(header_get("content-type", "") if callable(header_get) else "").split(";", 1)[0].strip()
    guessed_extension = (mimetypes.guess_extension(content_type) or "").lstrip(".")
    inferred_extension = inferred_extension or guessed_extension
    if inferred_extension:
        filename = f"{filename}.{inferred_extension}"
    return filename, inferred_extension


def looks_like_storage_filename(filename: str) -> bool:
    suffix = Path(filename).suffix.lstrip(".").lower()
    stem = Path(filename).stem
    return suffix in {"file", "tmp", "bin"} or bool(re.fullmatch(r"[A-Za-z0-9_-]{24,}", stem))


def emit_output(content: str, title: str, args: argparse.Namespace) -> None:
    metadata = getattr(args, "doc_metadata", None)
    if isinstance(metadata, dict):
        content = markdown_metadata_header(metadata) + content.lstrip()
    threshold = int(getattr(args, "path_threshold", 2000))
    requested = set(getattr(args, "with_parts", []) or [])
    force_path = bool(getattr(args, "output_path", False)) or "img-local" in requested
    if not force_path and len(content) <= threshold:
        print(content, end="")
        return
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_name = safe_filename(title)
    filename = f"{doc_name}.md"
    output_path = output_dir / filename
    if "img-local" in requested:
        assets_dir = output_path.parent / ".assets"
        content = localize_markdown_images(content, assets_dir, doc_name, default_browser_state_path().expanduser().resolve())
    content = relativize_local_image_paths(content, output_path.parent)
    node_id = str(getattr(args, "current_node_id", "") or "")
    cache = getattr(args, "cache", None)
    if can_use_global_markdown_cache(args, node_id):
        cache_path = output_cache_path_for_title(args, node_id, markdown_title(title), "md", "markdown")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")
        output_path = materialize_output(cache_path, output_path, args)
        write_output_cache_metadata(cache, cache_path, node_id, markdown_title(title), "md", "markdown", args, output_path=output_path, mode="markdown")
    else:
        output_path.write_text(content, encoding="utf-8")
    print(json_dump({"outputPath": str(output_path), "bytes": output_path.stat().st_size, "chars": len(content)}))


def markdown_title(title: str) -> str:
    return re.sub(r"\.(adoc|alidoc)$", "", title, flags=re.IGNORECASE)


def markdown_metadata_header(metadata: dict[str, object]) -> str:
    lines = ["<!-- DingTalk document metadata", ""]
    for label, key in (
        ("Original URL", "url"),
        ("Created By", "creator"),
        ("Created Time", "createTime"),
        ("Updated By", "modifier"),
        ("Updated Time", "modifiedTime"),
    ):
        value = metadata.get(key)
        if value:
            lines.append(f"{label}: {value}")
    lines.extend(["", "-->", ""])
    return "\n".join(lines)


def node_markdown_metadata(node: dict[str, object], fallback_url: str = "") -> dict[str, object]:
    creator = node.get("creator") if isinstance(node.get("creator"), dict) else {}
    modifier = node.get("modifier") if isinstance(node.get("modifier"), dict) else {}
    creator_name = cast(dict[str, object], creator).get("name") or node.get("creatorName") or node.get("creatorId")
    modifier_name = cast(dict[str, object], modifier).get("name") or node.get("modifierName") or node.get("modifierId")
    return {
        "url": node.get("url") or fallback_url,
        "creator": creator_name,
        "createTime": node.get("createTime") or node.get("createdTime"),
        "modifier": modifier_name,
        "modifiedTime": node.get("modifiedTime") or node.get("updatedTime"),
    }


def unique_output_path(output_dir: Path, filename: str) -> Path:
    return output_dir / filename


def output_path_for_title(args: argparse.Namespace, title: str, extension: str) -> Path:
    output_dir = Path(args.output_dir).expanduser().resolve()
    filename = safe_filename(title)
    normalized_extension = extension.lower().lstrip(".")
    if normalized_extension and not filename.lower().endswith("." + normalized_extension):
        filename = f"{filename}.{normalized_extension}"
    return unique_output_path(output_dir, filename)


def output_cache_mode(args: argparse.Namespace, mode: str | None = None) -> str:
    return mode or str(getattr(args, "mode", "file") or "file")


def output_cache_key(node_id: str, args: argparse.Namespace, extension: str, mode: str | None = None) -> dict[str, object]:
    cache_mode = output_cache_mode(args, mode)
    with_parts = [] if cache_mode in {"file", "pdf2text"} else sorted(str(item) for item in (getattr(args, "with_parts", []) or []))
    return {
        "nodeId": node_id,
        "mode": cache_mode,
        "extension": extension.lower().lstrip("."),
        "with": with_parts,
    }


def output_cache_path_for_title(args: argparse.Namespace, node_id: str, title: str, extension: str, mode: str | None = None) -> Path:
    cache_dir = Path(getattr(args, "output_cache_dir", str(default_output_cache_dir()))).expanduser().resolve()
    cache_mode = output_cache_mode(args, mode)
    filename = output_path_for_title(argparse.Namespace(output_dir=str(cache_dir)), title, extension).name
    return cache_dir / safe_filename(node_id or "unknown-node") / safe_filename(cache_mode) / filename


def same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


def materialize_output(cache_path: Path, output_path: Path, args: argparse.Namespace) -> Path:
    output_path = output_path.expanduser().resolve()
    cache_path = cache_path.expanduser().resolve()
    if same_path(cache_path, output_path):
        return cache_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() or output_path.is_symlink():
        with contextlib.suppress(OSError):
            output_path.unlink()
    strategy = str(getattr(args, "output_strategy", "link") or "link")
    if strategy == "copy":
        shutil.copy2(cache_path, output_path)
    else:
        try:
            os.link(cache_path, output_path)
        except OSError:
            output_path.symlink_to(cache_path)
    return output_path


def can_use_global_markdown_cache(args: argparse.Namespace, node_id: str) -> bool:
    requested = set(getattr(args, "with_parts", []) or [])
    return bool(node_id) and "img-local" not in requested and bool(metadata_updated_time(args))


def metadata_updated_time(args: argparse.Namespace) -> str:
    metadata = getattr(args, "doc_metadata", None)
    if not isinstance(metadata, dict):
        return ""
    return str(metadata.get("modifiedTime") or metadata.get("updatedTime") or "")


def markdown_header_value(path: Path, label: str) -> str:
    if not path.exists():
        return ""
    head = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    if not head.startswith("<!-- DingTalk document metadata"):
        return ""
    match = re.search(rf"^{re.escape(label)}:\s*(.+?)\s*$", head, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def cached_markdown_path(title: str, args: argparse.Namespace, cache: Cache | None = None, node_id: str = "") -> Path | None:
    path = output_path_for_title(args, markdown_title(title), "md")
    if cache is not None and can_use_global_markdown_cache(args, node_id):
        cache_path = cached_output_cache_path(cache, node_id, args, "md", "markdown")
        if cache_path is not None:
            return materialize_output(cache_path, path, args)
    expected_updated = metadata_updated_time(args)
    if expected_updated and path.exists() and markdown_header_value(path, "Updated Time") == expected_updated:
        if cache is not None and can_use_global_markdown_cache(args, node_id):
            cache_path = output_cache_path_for_title(args, node_id, markdown_title(title), "md", "markdown")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            if not cache_path.exists():
                shutil.copy2(path, cache_path)
            write_output_cache_metadata(cache, cache_path, node_id, markdown_title(title), "md", "markdown", args, output_path=path, mode="markdown")
        return path
    return None


def sidecar_metadata_path(path: Path) -> Path:
    return path.with_name(path.name + ".meta.json")


def cached_sidecar_matches(path: Path, node_id: str, args: argparse.Namespace) -> bool:
    if not path.exists():
        return False
    expected_updated = metadata_updated_time(args)
    if not expected_updated:
        return False
    sidecar = sidecar_metadata_path(path)
    if not sidecar.exists():
        return False
    try:
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return str(metadata.get("nodeId") or "") == node_id and str(metadata.get("modifiedTime") or "") == expected_updated


def cached_output_cache_path(cache: Cache | None, node_id: str, args: argparse.Namespace, extension: str, mode: str | None = None) -> Path | None:
    if cache is None:
        return None
    expected_updated = metadata_updated_time(args)
    if not expected_updated:
        return None
    metadata = cache.get_persistent("output", output_cache_key(node_id, args, extension, mode)) or {}
    if str(metadata.get("nodeId") or "") != node_id or str(metadata.get("modifiedTime") or "") != expected_updated:
        return None
    cache_path = Path(str(metadata.get("cachePath") or metadata.get("path") or "")).expanduser()
    if cache_path.exists():
        return cache_path.resolve()
    return None


def cached_output_matches(cache: Cache | None, path: Path, node_id: str, args: argparse.Namespace) -> bool:
    # Compatibility for older path-keyed output cache entries and sidecars.
    if cache is None or not path.exists():
        return False
    expected_updated = metadata_updated_time(args)
    if not expected_updated:
        return False
    metadata = cache.get_persistent("output", {"path": str(path.resolve())}) or {}
    return str(metadata.get("nodeId") or "") == node_id and str(metadata.get("modifiedTime") or "") == expected_updated


def read_sidecar_metadata(path: Path) -> dict[str, object]:
    sidecar = sidecar_metadata_path(path)
    if not sidecar.exists():
        return {}
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_sidecar_metadata(path: Path, node_id: str, title: str, extension: str, method: str, args: argparse.Namespace) -> None:
    metadata = getattr(args, "doc_metadata", None)
    payload = {
        "nodeId": node_id,
        "name": title,
        "extension": extension,
        "modifiedTime": metadata_updated_time(args),
        "method": method,
    }
    if isinstance(metadata, dict):
        payload["source"] = metadata
    sidecar_metadata_path(path).write_text(json_dump(payload) + "\n", encoding="utf-8")


def write_output_cache_metadata(cache: Cache | None, cache_path: Path, node_id: str, title: str, extension: str, method: str, args: argparse.Namespace, output_path: Path | None = None, mode: str | None = None) -> None:
    if cache is None:
        return
    metadata = getattr(args, "doc_metadata", None)
    key = output_cache_key(node_id, args, extension, mode)
    existing = cache.get_persistent("output", key) or {}
    outputs = [str(item) for item in existing.get("outputs", [])] if isinstance(existing.get("outputs"), list) else []
    if output_path is not None:
        output = str(output_path.resolve())
        if output not in outputs:
            outputs.append(output)
    payload = {
        "cachePath": str(cache_path.resolve()),
        "outputs": outputs,
        "nodeId": node_id,
        "name": title,
        "extension": extension,
        "modifiedTime": metadata_updated_time(args),
        "method": method,
        "mode": output_cache_mode(args, mode),
    }
    if isinstance(metadata, dict):
        payload["source"] = metadata
    cache.set("output", key, payload)


ZIP_BASED_EXTENSIONS = {"docx", "xlsx", "pptx", "zip"}
OLE_EXTENSIONS = {"doc", "xls", "ppt"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def sniff_file_kind(path: Path) -> str:
    with path.open("rb") as file:
        head = file.read(4096)
    stripped = head.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")
    lower = stripped[:128].lower()
    if head.startswith(b"Cr24"):
        return "crx"
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06") or head.startswith(b"PK\x07\x08"):
        return "zip"
    if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "ole"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "webp"
    if lower.startswith((b"<!doctype html", b"<html", b"<head", b"<body")):
        return "html"
    return "unknown"


def validate_downloaded_file(path: Path, extension: str) -> None:
    if not path.exists() or path.stat().st_size <= 0:
        raise DingTalkError(f"downloaded file is empty: {path.name}")
    expected = extension.lower().lstrip(".")
    kind = sniff_file_kind(path)
    if kind == "crx" and expected != "crx":
        raise DingTalkError(f"downloaded Chrome extension package instead of {expected or 'target'} file: {path.name}")
    if kind == "html" and expected not in {"html", "htm"}:
        raise DingTalkError(f"downloaded HTML page instead of {expected or 'target'} file: {path.name}")
    if expected == "pdf" and kind != "pdf":
        raise DingTalkError(f"downloaded file is not a PDF: {path.name} detected={kind}")
    if expected in ZIP_BASED_EXTENSIONS and kind != "zip":
        raise DingTalkError(f"downloaded file is not a valid {expected.upper()} container: {path.name} detected={kind}")
    if expected in OLE_EXTENSIONS and kind != "ole":
        raise DingTalkError(f"downloaded file is not a valid {expected.upper()} binary document: {path.name} detected={kind}")
    if expected in IMAGE_EXTENSIONS and kind not in IMAGE_EXTENSIONS:
        raise DingTalkError(f"downloaded file is not a valid image: {path.name} detected={kind}")


def download_candidate_ready(path: Path) -> bool:
    try:
        first_size = path.stat().st_size
        time.sleep(0.2)
        second_size = path.stat().st_size
    except OSError:
        return False
    return first_size > 0 and first_size == second_size


def wait_for_download(download_dir: Path, before: set[Path], extension: str, timeout_seconds: int = 90) -> Path:
    deadline = time.time() + timeout_seconds
    ignored: set[Path] = set()
    last_invalid = ""
    while time.time() < deadline:
        candidates = sorted(
            [path for path in download_dir.iterdir() if path.is_file() and path not in before and path not in ignored and not path.name.endswith((".crdownload", ".tmp"))],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            if not download_candidate_ready(candidate):
                continue
            try:
                validate_downloaded_file(candidate, extension)
                return candidate
            except DingTalkError as exc:
                last_invalid = str(exc)
                ignored.add(candidate)
        time.sleep(1)
    suffix = f"; last invalid download: {last_invalid}" if last_invalid else ""
    raise DingTalkError(f"download did not complete before timeout{suffix}")


def download_file_from_browser(url: str, title: str, extension: str, args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cached_path = output_path_for_title(args, title, extension)
    node_id = str(getattr(args, "current_node_id", "") or "")
    if node_id and (cached_output_matches(getattr(args, "cache", None), cached_path, node_id, args) or cached_sidecar_matches(cached_path, node_id, args)):
        return cached_path
    download_dir = output_dir / ".downloads-tmp"
    download_dir.mkdir(parents=True, exist_ok=True)
    before = set(download_dir.iterdir())
    state_path = default_browser_state_path().expanduser().resolve()
    session = browser_session_for(f"download:{url}")
    slot = browser_session_slot(session)
    slot.__enter__()
    open_agent_browser_for_login(["--session", session, "--state", str(state_path), "--download-path", str(download_dir)], url)
    run_agent_browser(["--session", session, "wait", "5000"], timeout=120)
    payload = cast(dict[str, object], run_agent_browser([
        "--session",
        session,
        "eval",
        r'''
(() => {
  const visible = el => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  for (const frame of document.querySelectorAll('iframe')) {
    try {
      const doc = frame.contentDocument;
      const button = doc && doc.querySelector('[data-testid="download"], [data-role="download"]');
      if (visible(button)) {
        const frameRect = frame.getBoundingClientRect();
        const buttonRect = button.getBoundingClientRect();
        return {
          found: true,
          x: Math.round(frameRect.left + buttonRect.left + buttonRect.width / 2),
          y: Math.round(frameRect.top + buttonRect.top + buttonRect.height / 2)
        };
      }
    } catch (_) {}
  }
  const button = document.querySelector('[data-testid="download"], [data-role="download"]');
  if (visible(button)) {
    const rect = button.getBoundingClientRect();
    return { found: true, x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
  }
  return { found: false };
})()
''',
        "--json",
    ], parse_json=True, timeout=120))
    data = payload.get("data")
    result = cast(dict[str, object], data).get("result") if isinstance(data, dict) else {}
    if not isinstance(result, dict) or not result.get("found"):
        slot.__exit__(None, None, None)
        raise DingTalkError("download button was not found in DingTalk preview page")
    x = int(result.get("x") or 0)
    y = int(result.get("y") or 0)
    try:
        run_agent_browser(["--session", session, "mouse", "move", str(x), str(y)], timeout=120)
        run_agent_browser(["--session", session, "mouse", "down"], timeout=120)
        run_agent_browser(["--session", session, "mouse", "up"], timeout=120)
        downloaded = wait_for_download(download_dir, before, extension)
        filename = safe_filename(title)
        if extension and not filename.lower().endswith("." + extension.lower()):
            filename = f"{filename}.{extension}"
        output_path = unique_output_path(output_dir, filename)
        shutil.move(str(downloaded), str(output_path))
        return output_path
    finally:
        slot.__exit__(None, None, None)


def download_file_with_official_api(client: DingTalkClient, node_id: str, title: str, extension: str, args: argparse.Namespace) -> Path:
    cached_path = output_path_for_title(args, title, extension)
    if cached_output_matches(getattr(args, "cache", None), cached_path, node_id, args) or cached_sidecar_matches(cached_path, node_id, args):
        return cached_path
    dentry_mapping = client.query_dentry_id_by_uuid(node_id)
    space_id = str(dentry_mapping.get("spaceId") or "")
    dentry_id = str(dentry_mapping.get("dentryId") or "")
    if not space_id.isdigit() or not dentry_id.isdigit():
        raise DingTalkError("queryDentryId did not return numeric spaceId/dentryId")
    download_info = client.file_download_info(space_id, dentry_id)
    signature_info = download_info.get("headerSignatureInfo")
    if not isinstance(signature_info, dict):
        raise DingTalkError("official download API did not return headerSignatureInfo")
    urls = signature_info.get("internalResourceUrls") or signature_info.get("resourceUrls") or []
    if not isinstance(urls, list) or not urls:
        raise DingTalkError("official download API did not return resource URLs")
    headers_obj = signature_info.get("headers") or {}
    if not isinstance(headers_obj, dict):
        headers_obj = {}
    headers = {str(key): str(value) for key, value in headers_obj.items()}
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(str(urls[0]), headers=headers)
    with urllib.request.urlopen(req, timeout=120) as response:
        filename, _inferred_extension = filename_from_download_response(title, extension, str(urls[0]), response.headers)
        if title and (not Path(filename).suffix or looks_like_storage_filename(filename)):
            fallback_filename = safe_filename(title)
            fallback_extension = extension.lower().lstrip(".") or Path(filename).suffix.lstrip(".").lower()
            if fallback_extension and not fallback_filename.lower().endswith("." + fallback_extension):
                fallback_filename = f"{fallback_filename}.{fallback_extension}"
            filename = fallback_filename
        output_path = unique_output_path(output_dir, filename)
        output_path.write_bytes(response.read())
        try:
            validate_downloaded_file(output_path, _inferred_extension or extension)
        except DingTalkError:
            with contextlib.suppress(OSError):
                output_path.unlink()
            raise
    return output_path


def download_file_with_preview_resource(client: DingTalkClient, node_id: str, title: str, extension: str, args: argparse.Namespace) -> Path:
    cached_path = output_path_for_title(args, title, extension)
    if cached_output_matches(getattr(args, "cache", None), cached_path, node_id, args) or cached_sidecar_matches(cached_path, node_id, args):
        return cached_path
    dentry_mapping = client.query_dentry_id_by_uuid(node_id)
    space_id = str(dentry_mapping.get("spaceId") or "")
    dentry_id = str(dentry_mapping.get("dentryId") or "")
    if not space_id.isdigit() or not dentry_id.isdigit():
        raise DingTalkError("queryDentryId did not return numeric spaceId/dentryId for preview resource")
    url = "https://space.dingtalk.com/attachment/mdown?" + urllib.parse.urlencode({
        "bizid": space_id,
        "objectid": dentry_id,
        "version": "1",
        "operate": "preview",
    })
    state_path = default_browser_state_path().expanduser().resolve()
    if not state_path.exists():
        ensure_default_browser_state(state_path, f"https://alidocs.dingtalk.com/i/nodes/{node_id}", emit=False)
    cookie_header = cookie_header_from_browser_state_for_domain(state_path, "dingtalk.com")
    if not cookie_header:
        raise DingTalkError("browser state does not contain DingTalk cookies for preview resource download")
    headers = {
        "Accept": "application/pdf,application/octet-stream,*/*",
        "Cookie": cookie_header,
        "Referer": "https://alidocs.dingtalk.com/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    }
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            filename, inferred_extension = filename_from_download_response(title, extension, url, response.headers)
            if title and (not Path(filename).suffix or looks_like_storage_filename(filename)):
                fallback_filename = safe_filename(title)
                fallback_extension = extension.lower().lstrip(".") or inferred_extension
                if fallback_extension and not fallback_filename.lower().endswith("." + fallback_extension):
                    fallback_filename = f"{fallback_filename}.{fallback_extension}"
                filename = fallback_filename
            output_path = unique_output_path(output_dir, filename)
            output_path.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        raise DingTalkError(f"preview resource download failed: HTTP {exc.code} {exc.reason}") from exc
    try:
        validate_downloaded_file(output_path, inferred_extension or extension)
    except DingTalkError:
        with contextlib.suppress(OSError):
            output_path.unlink()
        raise
    return output_path


def download_non_alidoc_file(client: DingTalkClient, url: str, node_id: str, title: str, extension: str, args: argparse.Namespace) -> tuple[Path, str]:
    try:
        return download_file_with_official_api(client, node_id, title, extension, args), "official-api"
    except DingTalkError as official_error:
        try:
            return download_file_with_preview_resource(client, node_id, title, extension, args), "preview-resource"
        except DingTalkError:
            try:
                return download_file_from_browser(url, title, extension, args), "browser-fallback"
            except DingTalkError as browser_error:
                raise DingTalkError(f"official API failed: {official_error}; browser fallback failed: {browser_error}") from browser_error


def should_try_preview_text_fallback(error: DingTalkError) -> bool:
    text = str(error).lower()
    return any(
        token in text
        for token in (
            "download button was not found",
            "download did not complete",
            "downloaded chrome extension",
            "downloaded html page",
            "downloaded file is not",
            "not a valid",
        )
    )


def preview_markdown_from_browser(url: str, title: str, extension: str, args: argparse.Namespace) -> str:
    state_path = default_browser_state_path().expanduser().resolve()
    if not state_path.exists():
        ensure_default_browser_state(state_path, url, emit=False)
    session = browser_session_for(f"preview:{url}")
    script = r'''
(() => {
  const clean = text => String(text || '')
    .replace(/\u00a0/g, ' ')
    .split(/\n+/)
    .map(line => line.replace(/\s+/g, ' ').trim())
    .filter(line => line)
    .join('\n');
  const visible = el => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const looksLikeChromeText = text => {
    const lower = text.toLowerCase();
    return lower.includes('using dingtalk document preview')
      || lower.includes('recently modified')
      || lower.includes('files modified locally need to be updated')
      || lower.includes('directory tree icon updated')
      || lower.includes('resource load timed out')
      || lower.includes('please check the network and try again')
      || /\b(home|catalog|team files|recently opened|share|search)\b/i.test(text.slice(0, 300));
  };
  const collectDoc = doc => {
    const selectors = [
      '[class*="textLayer" i]',
      '[class*="text-layer" i]',
      '[class*="pageText" i]',
      '[class*="page-text" i]',
      '[data-page-number]',
      '[role="document"]',
      '[class*="page" i]',
      '[class*="viewer" i]'
    ];
    const seen = new Set();
    const candidates = [];
    for (const selector of selectors) {
      for (const el of doc.querySelectorAll(selector)) {
        if (seen.has(el) || !visible(el)) continue;
        seen.add(el);
        const text = clean(el.innerText || el.textContent || '');
        if (text.length >= 80 && !looksLikeChromeText(text)) candidates.push({ text, selector });
      }
    }
    return candidates;
  };
  const candidates = [];
  const visitDoc = (doc, depth = 0) => {
    if (!doc || depth > 3) return;
    candidates.push(...collectDoc(doc));
    for (const nested of doc.querySelectorAll('iframe')) {
      try {
        const nestedDoc = nested.contentDocument || nested.contentWindow?.document;
        if (nestedDoc) visitDoc(nestedDoc, depth + 1);
      } catch (_) {}
    }
  };
  if (/\/uni-preview|\/preview/.test(location.pathname)) {
    visitDoc(document);
  }
  const frameStates = [];
  for (const frame of document.querySelectorAll('iframe')) {
    try {
      const doc = frame.contentDocument || frame.contentWindow?.document;
      const text = clean(doc?.body?.innerText || doc?.body?.textContent || '');
      frameStates.push({ src: frame.src, text: text.slice(0, 300) });
      if (doc) visitDoc(doc);
    } catch (error) {
      frameStates.push({ src: frame.src, error: String(error) });
    }
  }
  candidates.sort((a, b) => b.text.length - a.text.length);
  const best = candidates[0] || { text: '', selector: '' };
  return {
    text: best.text,
    selector: best.selector,
    href: location.href,
    title: document.title,
    frameStates,
    iframeCount: document.querySelectorAll('iframe').length,
    canvasCount: document.querySelectorAll('canvas').length,
    imageCount: document.querySelectorAll('img').length
  };
})()
'''
    with browser_session_slot(session):
        open_agent_browser_for_login(["--session", session, "--state", str(state_path)], url)
        run_agent_browser(["--session", session, "wait", str(default_browser_wait_ms() + 3000)], timeout=120)
        run_agent_browser(["--session", session, "state", "save", str(state_path)], timeout=120)
        payload = cast(dict[str, object], run_agent_browser(["--session", session, "eval", script, "--json"], parse_json=True, timeout=120))
    data = payload.get("data")
    result = cast(dict[str, object], data).get("result") if isinstance(data, dict) else {}
    if not isinstance(result, dict):
        raise DingTalkError("DingTalk preview did not return extractable text")
    text = str(result.get("text") or "").strip()
    frame_states = result.get("frameStates") if isinstance(result.get("frameStates"), list) else []
    frame_text = "\n".join(str(item.get("text") or "") for item in frame_states if isinstance(item, dict))
    if re.search(r"resource load timed out|资源加载超时|加载超时", frame_text, flags=re.IGNORECASE):
        raise DingTalkError("DingTalk preview loaded, but the embedded preview resource timed out before text could be extracted")
    if re.search(r"Using DingTalk Document Preview|Recently modified|Files modified locally need to be updated|Directory tree icon updated", text, flags=re.IGNORECASE):
        raise DingTalkError("DingTalk preview exposed only viewer chrome, not document body text")
    if len(text) < 80:
        raise DingTalkError(
            "DingTalk preview is viewable, but no selectable text layer was found; "
            f"it may be rendered as images/canvas only (canvas={result.get('canvasCount')}, images={result.get('imageCount')})"
        )
    label = extension.upper() if extension else "file"
    return "\n".join([
        f"# {markdown_title(title)}",
        "",
        f"> Preview-only extraction from DingTalk {label}. The original file could not be downloaded, so formatting may be incomplete.",
        "",
        text,
        "",
    ])


def read_pdf_text_mode_enabled(args: argparse.Namespace, path: Path, extension: str) -> bool:
    mode = str(getattr(args, "mode", "file") or "file")
    actual_extension = (extension or path.suffix.lstrip(".")).lower().lstrip(".")
    return mode == "pdf2text" and actual_extension == "pdf"


def pdf_text_install_hint() -> str:
    return "pdftotext is required for --mode pdf2text; install poppler-utils, for example: sudo apt install poppler-utils"


def convert_pdf_to_text(path: Path) -> Path | None:
    binary = shutil.which("pdftotext")
    if not binary:
        return None
    output_path = path.with_suffix(".txt")
    subprocess.run([binary, "-layout", str(path), str(output_path)], check=True, timeout=120)
    return output_path


def read_non_alidoc_file(client: DingTalkClient, url: str, node_id: str, title: str, extension: str, args: argparse.Namespace) -> int:
    try:
        args.current_node_id = node_id
        cache = getattr(args, "cache", None)
        requested_output_path = output_path_for_title(args, title, extension)
        cache_file_path = cached_output_cache_path(cache, node_id, args, extension, "file")
        file_cached_before = cache_file_path is not None
        method = "cache"
        if cache_file_path is None:
            cache_file_path = output_cache_path_for_title(args, node_id, title, extension, "file")
            original_output_dir = args.output_dir
            args.output_dir = str(cache_file_path.parent)
            try:
                cache_file_path, method = download_non_alidoc_file(client, url, node_id, title, extension, args)
            finally:
                args.output_dir = original_output_dir
        output_path = materialize_output(cache_file_path, requested_output_path, args)
        if file_cached_before:
            method = str(read_sidecar_metadata(cache_file_path).get("method") or method)
        write_sidecar_metadata(cache_file_path, node_id, title, extension, method, args)
        write_output_cache_metadata(cache, cache_file_path, node_id, title, extension, method, args, output_path=output_path, mode="file")
        if read_pdf_text_mode_enabled(args, output_path, extension):
            requested_text_path = requested_output_path.with_suffix(".txt")
            cache_text_path = cached_output_cache_path(cache, node_id, args, "txt", "pdf2text")
            text_cached_before = cache_text_path is not None
            if cache_text_path is None:
                generated_text_path = convert_pdf_to_text(cache_file_path)
                if generated_text_path is not None:
                    cache_text_path = output_cache_path_for_title(args, node_id, Path(title).stem, "txt", "pdf2text")
                    cache_text_path.parent.mkdir(parents=True, exist_ok=True)
                    if not same_path(generated_text_path, cache_text_path):
                        if cache_text_path.exists() or cache_text_path.is_symlink():
                            cache_text_path.unlink()
                        shutil.move(str(generated_text_path), str(cache_text_path))
                    write_sidecar_metadata(cache_text_path, node_id, title, "txt", f"{method}+pdftotext", args)
            if cache_text_path is None:
                emit_download_result(output_path, node_id, title, extension, method, warning=pdf_text_install_hint())
                return 0
            text_path = materialize_output(cache_text_path, requested_text_path, args)
            write_output_cache_metadata(cache, cache_text_path, node_id, title, "txt", f"{method}+pdftotext", args, output_path=text_path, mode="pdf2text")
            emit_pdf_text_result(text_path, output_path, node_id, title, method, cached=text_cached_before)
            return 0
        emit_download_result(output_path, node_id, title, extension, method, cached=file_cached_before)
        return 0
    except DingTalkError as exc:
        if not should_try_preview_text_fallback(exc):
            raise
        content = preview_markdown_from_browser(url, title, extension, args)
        emit_output(content, markdown_title(title), args)
        return 0


def read_dlink_from_browser(url: str, title: str, args: argparse.Namespace) -> int:
    requested = set(args.with_parts or [])
    content = private_markdown_with_session(
        url,
        default_browser_state_path().expanduser().resolve(),
        default_browser_wait_ms(),
        include_diagram="diagram" in requested,
    )
    if "img" in requested:
        content = proxify_markdown_images(content, args.proxy_port)
    output_title = markdown_title(dlink_base_title(title) or title)
    emit_output(content, output_title, args)
    return 0


def emit_download_result(path: Path, node_id: str, title: str, extension: str, method: str, warning: str = "", cached: bool = False) -> None:
    actual_extension = extension or path.suffix.lstrip(".")
    payload: dict[str, object] = {"outputPath": str(path), "bytes": path.stat().st_size, "name": path.name, "nodeId": node_id, "extension": actual_extension, "kind": "file-download", "method": method}
    if warning:
        payload["warning"] = warning
    if cached:
        payload["cached"] = True
    print(json_dump(payload))


def emit_pdf_text_result(path: Path, source_pdf_path: Path, node_id: str, title: str, method: str, cached: bool = False) -> None:
    payload: dict[str, object] = {
        "outputPath": str(path),
        "bytes": path.stat().st_size,
        "name": path.name,
        "nodeId": node_id,
        "extension": "txt",
        "kind": "pdf-text",
        "method": f"{method}+pdftotext",
        "sourcePdfPath": str(source_pdf_path),
    }
    if cached:
        payload["cached"] = True
    print(json_dump(payload))


def notable_record_value_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "; ".join(notable_record_value_to_text(item) for item in value if item is not None)
    if isinstance(value, dict):
        for key in ("text", "name", "title", "value", "url"):
            item = value.get(key)
            if isinstance(item, (str, int, float, bool)):
                return str(item)
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def notable_records_to_csv(fields: list[str], records: list[dict[str, object]]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["record_id", *fields], extrasaction="ignore")
    writer.writeheader()
    for record in records:
        values = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        row = {"record_id": str(record.get("id") or "")}
        for field in fields:
            row[field] = notable_record_value_to_text(cast(dict[str, object], values).get(field))
        writer.writerow(row)
    return output.getvalue()


def column_label(index: int) -> str:
    label = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label or "A"


def spreadsheet_cell_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "".join(spreadsheet_cell_to_text(item) for item in value)
    if isinstance(value, dict):
        if value.get("type") == "richText" and isinstance(value.get("texts"), list):
            return "".join(spreadsheet_cell_to_text(item) for item in value.get("texts", []))
        if "text" in value:
            return spreadsheet_cell_to_text(value.get("text"))
        if "value" in value:
            return spreadsheet_cell_to_text(value.get("value"))
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def rows_to_csv(rows: list[list[object]]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow([spreadsheet_cell_to_text(cell) for cell in row])
    return output.getvalue()


def read_workbook_to_csv(client: DingTalkClient, workbook_id: str, title: str, args: argparse.Namespace) -> None:
    sheets_payload = client.workbook_sheets(workbook_id)
    sheets = sheets_payload.get("value") if isinstance(sheets_payload.get("value"), list) else []
    if not sheets:
        raise DingTalkError("workbook has no readable sheets")
    output_dir = Path(args.output_dir).expanduser().resolve()
    workbook_name = safe_filename(re.sub(r"\.axls$", "", title, flags=re.IGNORECASE))
    workbook_dir = output_dir / workbook_name
    workbook_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, object]] = []
    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue
        sheet_id = str(sheet.get("id") or "")
        sheet_name = str(sheet.get("name") or sheet_id or "sheet")
        if not sheet_id:
            continue
        detail = client.workbook_sheet(workbook_id, sheet_id)
        last_row = int(detail.get("lastNonEmptyRow") or detail.get("rowCount") or 0)
        last_col = int(detail.get("lastNonEmptyColumn") or detail.get("columnCount") or 0)
        if last_row <= 0 or last_col <= 0:
            rows: list[list[object]] = []
        else:
            range_address = f"A1:{column_label(last_col)}{last_row}"
            range_payload = client.workbook_range(workbook_id, sheet_id, range_address)
            values = range_payload.get("values")
            rows = cast(list[list[object]], values if isinstance(values, list) else [])
        output_path = unique_output_path(workbook_dir, safe_filename(sheet_name) + ".csv")
        output_path.write_text(rows_to_csv(rows), encoding="utf-8-sig")
        outputs.append({"sheetId": sheet_id, "sheetName": sheet_name, "outputPath": str(output_path), "rows": len(rows), "columns": last_col, "bytes": output_path.stat().st_size})
    print(json_dump({"kind": "workbook-csv", "workbookId": workbook_id, "name": title, "outputDir": str(workbook_dir), "sheets": outputs}))


def read_notable_base_to_csv(client: DingTalkClient, base_id: str, title: str, args: argparse.Namespace) -> None:
    sheets_payload = client.notable_sheets(base_id)
    sheets = sheets_payload.get("value") if isinstance(sheets_payload.get("value"), list) else []
    if not sheets:
        raise DingTalkError("AI table has no readable sheets or Notable API returned no sheets")
    sheet_count = len(sheets)
    size = int(getattr(args, "node_size", 0) or 0)
    force_all = bool(getattr(args, "all_sheets", False))
    if not force_all and (sheet_count > int(getattr(args, "sheet_confirm_threshold", 10)) or size > int(getattr(args, "large_table_threshold", 50 * 1024 * 1024))):
        print(json_dump({
            "kind": "ai-table-csv",
            "readable": False,
            "reason": "large AI table requires explicit --all-sheets to export all sheets",
            "baseId": base_id,
            "name": title,
            "size": size,
            "sheetCount": sheet_count,
            "sheets": [{"sheetId": str(sheet.get("id") or ""), "sheetName": str(sheet.get("name") or "")} for sheet in sheets if isinstance(sheet, dict)],
            "hint": "Re-run with --all-sheets if you want to export everything. It may be slow and can hit DingTalk 503 on very large tables.",
        }))
        return
    output_dir = Path(args.output_dir).expanduser().resolve()
    base_name = safe_filename(re.sub(r"\.able$", "", title, flags=re.IGNORECASE))
    base_dir = output_dir / base_name
    base_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, object]] = []
    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue
        sheet_id = str(sheet.get("id") or "")
        sheet_name = str(sheet.get("name") or sheet_id or "sheet")
        if not sheet_id:
            continue
        fields_payload = client.notable_fields(base_id, sheet_id)
        field_items = fields_payload.get("value") if isinstance(fields_payload.get("value"), list) else []
        fields = [str(field.get("name") or "") for field in field_items if isinstance(field, dict) and field.get("name")]
        records: list[dict[str, object]] = []
        next_token = ""
        while True:
            payload = client.notable_records(base_id, sheet_id, max_results=100, next_token=next_token)
            page_records = payload.get("records") if isinstance(payload.get("records"), list) else []
            records.extend(cast(list[dict[str, object]], [record for record in page_records if isinstance(record, dict)]))
            if not payload.get("hasMore"):
                break
            next_token = str(payload.get("nextToken") or "")
            if not next_token:
                break
        filename = safe_filename(sheet_name) + ".csv"
        output_path = unique_output_path(base_dir, filename)
        output_path.write_text(notable_records_to_csv(fields, records), encoding="utf-8-sig")
        outputs.append({"sheetId": sheet_id, "sheetName": sheet_name, "outputPath": str(output_path), "records": len(records), "fields": len(fields), "bytes": output_path.stat().st_size})
    print(json_dump({"kind": "ai-table-csv", "baseId": base_id, "name": title, "outputDir": str(base_dir), "sheets": outputs}))


def relativize_local_image_paths(markdown: str, base_dir: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        alt = match.group(1)
        target = match.group(2)
        if target.startswith(("http://", "https://", "file://")):
            return match.group(0)
        path = Path(target).expanduser()
        if not path.is_absolute() or not path.exists():
            return match.group(0)
        rel = Path(os_path_rel(path, base_dir)).as_posix()
        return f"![{alt}]({rel})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, markdown)


def os_path_rel(path: Path, start: Path) -> str:
    # Path.relative_to only works for strict ancestry; os.path.relpath handles siblings.
    import os

    return os.path.relpath(path, start=start)


def render_blocks(title: str, blocks_payload: dict[str, object], mode: str, image_refs: list[str] | None = None) -> str:
    if mode == "markdown":
        if image_refs:
            return blocks_to_markdown_with_images(title, blocks_payload, image_refs)
        return blocks_to_markdown(title, blocks_payload)
    if mode == "text":
        return blocks_to_text(blocks_payload)
    if mode == "table":
        return json_dump({"title": title, "tableCount": len(extract_tables(blocks_payload)), "tables": extract_tables(blocks_payload)}) + "\n"
    if mode == "img":
        images = extract_image_like_blocks(blocks_payload)
        return json_dump({"title": title, "imageLikeCount": len(images), "imageLikeBlocks": images}) + "\n"
    if mode == "all":
        images = extract_image_like_blocks(blocks_payload)
        tables = extract_tables(blocks_payload)
        return json_dump(
            {
                "title": title,
                "markdown": blocks_to_markdown(title, blocks_payload),
                "text": blocks_to_text(blocks_payload),
                "tableCount": len(tables),
                "tables": tables,
                "imageLikeCount": len(images),
                "imageLikeBlocks": images,
                "blocks": block_list(blocks_payload),
            }
        ) + "\n"
    raise DingTalkError(f"unknown read mode: {mode}")


def normalize_search_item(item: dict[str, object]) -> dict[str, object]:
    return {
        "name": item.get("name") or item.get("title") or "",
        "dentryUuid": item.get("dentryUuid") or item.get("nodeId") or item.get("dentryId") or "",
        "creator": item.get("creator") or {},
        "modifier": item.get("modifier") or {},
        "path": item.get("path") or {},
    }


def dlink_base_title(title: str) -> str:
    return re.sub(r"\.(dlink|dlnk)$", "", title, flags=re.IGNORECASE).strip()


def resolve_dlink_target(client: DingTalkClient, cache: Cache, node_id: str, title: str) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    keyword = dlink_base_title(title)
    if not keyword:
        return None, []
    search_queries = [keyword]
    words = [item for item in re.split(r"[\s\-_]+", keyword) if item]
    if len(words) > 1:
        search_queries.extend(words)
    candidates: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for query in search_queries:
        payload = client.search_dentries(query, 20)
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("dentryUuid") or item.get("nodeId") or item.get("dentryId") or "")
            candidate_name = str(item.get("name") or item.get("title") or "")
            if not candidate_id or candidate_id == node_id or candidate_id in seen_ids:
                continue
            if dlink_base_title(candidate_name) != keyword:
                continue
            seen_ids.add(candidate_id)
            try:
                node = cache.cached("node", {"nodeId": candidate_id}, lambda candidate_id=candidate_id: client.get_node(candidate_id))
            except DingTalkError:
                continue
            extension = str(node.get("extension") or "")
            category = str(node.get("category") or "")
            normalized = {
                "nodeId": node.get("nodeId") or candidate_id,
                "name": node.get("name") or candidate_name,
                "extension": extension,
                "category": category,
                "url": node.get("url") or f"https://alidocs.dingtalk.com/i/nodes/{candidate_id}",
            }
            if extension not in {"dlink", "dlnk"} and str(node.get("type") or "").upper() != "FOLDER":
                candidates.append({**normalized, "node": node})
    if len(candidates) == 1:
        return cast(dict[str, object], candidates[0]["node"]), candidates
    return None, candidates


def find_assets(value: object, path: str = "$", assets: list[dict[str, object]] | None = None) -> list[dict[str, object]]:
    if assets is None:
        assets = []
    if isinstance(value, dict):
        block_type = value.get("blockType")
        if block_type == "attachment" and isinstance(value.get("attachment"), dict):
            attachment = cast(dict[str, object], value["attachment"])
            assets.append({"kind": "attachment", "path": path, "blockId": value.get("id"), **attachment})
        for key in ("image", "picture", "media"):
            if isinstance(value.get(key), dict):
                assets.append({"kind": key, "path": f"{path}.{key}", "blockId": value.get("id"), **cast(dict[str, object], value[key])})
        for key, child in value.items():
            find_assets(child, f"{path}.{key}", assets)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            find_assets(child, f"{path}[{index}]", assets)
    return assets


def cmd_search(client: DingTalkClient, cache: Cache, args: argparse.Namespace) -> int:
    keywords = [item for item in re.split(r"\s+", args.keyword.strip()) if item]
    if len(keywords) > 1:
        client.auth.token()
        results: list[dict[str, object]] = []
        errors: dict[str, str] = {}
        max_workers = max(1, min(int(getattr(args, "concurrency", 5)), 5, len(keywords)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(client.search_dentries, keyword, args.limit): keyword for keyword in keywords}
            for future in concurrent.futures.as_completed(futures):
                keyword = futures[future]
                try:
                    payload = future.result()
                except Exception as exc:
                    errors[keyword] = str(exc)
                    continue
                items = payload.get("items") if isinstance(payload.get("items"), list) else []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    normalized = normalize_search_item(cast(dict[str, object], item))
                    normalized["matchedKeyword"] = keyword
                    results.append(normalized)
        merged: dict[str, dict[str, object]] = {}
        for item in results:
            key = str(item.get("dentryUuid") or item.get("nodeId") or item.get("name") or json.dumps(item, ensure_ascii=False, sort_keys=True))
            if key not in merged:
                merged[key] = {**item, "matchedKeywords": [item.get("matchedKeyword")]}
            else:
                matched = cast(list[object], merged[key].setdefault("matchedKeywords", []))
                keyword = item.get("matchedKeyword")
                if keyword not in matched:
                    matched.append(keyword)
        merged_items = sorted(merged.values(), key=lambda item: len(cast(list[object], item.get("matchedKeywords") or [])), reverse=True)
        for item in merged_items:
            item.pop("matchedKeyword", None)
        print(json_dump({"keyword": args.keyword, "keywords": keywords, "mode": "split-any", "concurrency": max_workers, "errors": errors, "items": merged_items}))
        return 0
    payload = client.search_dentries(args.keyword, args.limit)
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    normalized = [normalize_search_item(cast(dict[str, object], item)) for item in items if isinstance(item, dict)]
    if args.raw:
        print(json_dump(payload))
    else:
        print(json_dump({"keyword": args.keyword, "nextToken": payload.get("nextToken") or "", "items": normalized}))
    return 0


def cmd_read(client: DingTalkClient, cache: Cache, args: argparse.Namespace) -> int:
    node_id = args.node_id
    if re.match(r"^https?://", node_id):
        args.url = node_id
        return cmd_read_url(client, cache, args)
    title = node_id
    extension = ""
    node: dict[str, object] = {}
    source_url = str(args.source_url or f"https://alidocs.dingtalk.com/i/nodes/{node_id}")
    try:
        node = cache.cached("node", {"nodeId": node_id}, lambda: client.get_node(node_id))
        title = str(node.get("name") or node.get("title") or node_id)
        extension = str(node.get("extension") or "")
        source_url = str(node.get("url") or source_url)
    except DingTalkError:
        title = node_id
    if node:
        reject_folder_node(node, node_id, title)
    if extension in {"dlink", "dlnk"}:
        target_node, candidates = resolve_dlink_target(client, cache, node_id, title)
        if target_node is not None:
            node = target_node
            node_id = str(node.get("nodeId") or node.get("dentryUuid") or "")
            title = str(node.get("name") or node.get("title") or node_id)
            extension = str(node.get("extension") or "")
            source_url = str(node.get("url") or f"https://alidocs.dingtalk.com/i/nodes/{node_id}")
            reject_folder_node(node, node_id, title)
        elif getattr(args, "format", "markdown") == "markdown":
            args.doc_metadata = node_markdown_metadata(node, source_url)
            args.source_url = source_url
            return read_dlink_from_browser(source_url, title, args)
        elif getattr(args, "format", "markdown") == "json":
            print(json_dump({
                "readable": False,
                "reason": "The node is a DingTalk shortcut (.dlink/.dlnk). No unique same-name non-shortcut target was found.",
                "nodeId": node_id,
                "name": title,
                "extension": extension,
                "candidates": [{key: value for key, value in candidate.items() if key != "node"} for candidate in candidates],
            }))
            return 2
    args.doc_metadata = node_markdown_metadata(node, source_url) if node else {"url": source_url}
    args.source_url = source_url
    args.current_node_id = node_id
    if extension and extension not in {"adoc", "alidoc"}:
        if extension == "able":
            args.node_size = int(node.get("size") or 0) if node else 0
            read_notable_base_to_csv(client, node_id, title, args)
            return 0
        if extension == "axls":
            read_workbook_to_csv(client, node_id, title, args)
            return 0
        return read_non_alidoc_file(client, source_url, node_id, title, extension, args)
    blocks_payload: dict[str, object] | None = None
    browser_fallback = False
    try:
        blocks_payload = cache.cached("blocks", {"docId": node_id}, lambda: client.read_blocks(node_id))
    except DingTalkError as exc:
        requested = set(args.with_parts or [])
        if not node and should_download_as_file(exc):
            search_item = cache.find_search_item(node_id)
            if search_item:
                title = str(search_item.get("name") or search_item.get("title") or title)
            inferred_extension = Path(title).suffix.lstrip(".").lower()
            return read_non_alidoc_file(client, source_url, node_id, title, inferred_extension, args)
        if args.format == "markdown" and args.source_url and (requested.intersection({"img", "img-origin", "img-local", "diagram"}) or should_use_browser_fallback(exc)):
            browser_fallback = True
        else:
            raise
    if args.format == "json":
        if blocks_payload is None:
            raise DingTalkError("raw json output is unavailable when blocks API access is denied")
        print(json_dump(blocks_payload))
    else:
        requested = set(args.with_parts or [])
        cached_path = cached_markdown_path(title, args, cache, node_id) if args.format == "markdown" and (bool(getattr(args, "output_path", False)) or "img-local" in requested) else None
        if cached_path is not None:
            print(json_dump({"outputPath": str(cached_path), "bytes": cached_path.stat().st_size, "chars": len(cached_path.read_text(encoding="utf-8")), "cached": True}))
            return 0
        if browser_fallback or requested.intersection({"img", "img-origin", "img-local", "diagram"}):
            content = private_markdown_with_session(
                source_url,
                default_browser_state_path().expanduser().resolve(),
                default_browser_wait_ms(),
                include_diagram="diagram" in requested,
            )
            if "img" in requested:
                content = proxify_markdown_images(content, args.proxy_port)
        elif blocks_payload is not None:
            content = blocks_to_markdown(markdown_title(title), blocks_payload)
        else:
            raise DingTalkError("document content is unavailable")
        emit_output(content, markdown_title(title), args)
    return 0


def cmd_resolve_url(client: DingTalkClient, cache: Cache, args: argparse.Namespace) -> int:
    print(json_dump(cache.cached("resolve-url", {"url": args.url}, lambda: client.query_node_by_url(args.url))))
    return 0


def cmd_read_url(client: DingTalkClient, cache: Cache, args: argparse.Namespace) -> int:
    node = cache.cached("resolve-url", {"url": args.url}, lambda: client.query_node_by_url(args.url))
    node_id = str(node.get("nodeId") or node.get("dentryUuid") or "")
    title = str(node.get("name") or node.get("title") or node_id)
    extension = str(node.get("extension") or "")
    category = str(node.get("category") or "")
    if not node_id:
        raise DingTalkError("URL resolved but no nodeId/dentryUuid was returned")
    reject_folder_node(node, node_id, title)
    if extension in {"dlink", "dlnk"}:
        target_node, candidates = resolve_dlink_target(client, cache, node_id, title)
        if target_node is None:
            if args.format == "markdown":
                args.doc_metadata = node_markdown_metadata(node, args.url)
                args.source_url = args.url
                return read_dlink_from_browser(args.url, title, args)
            print(json_dump({
                "readable": False,
                "reason": "The URL resolves to a DingTalk shortcut (.dlink/.dlnk). No unique same-name non-shortcut target was found.",
                "nodeId": node_id,
                "name": title,
                "extension": extension,
                "candidates": [{key: value for key, value in candidate.items() if key != "node"} for candidate in candidates],
            }))
            return 2
        node = target_node
        node_id = str(node.get("nodeId") or node.get("dentryUuid") or "")
        title = str(node.get("name") or node.get("title") or node_id)
        extension = str(node.get("extension") or "")
        category = str(node.get("category") or "")
        args.url = str(node.get("url") or f"https://alidocs.dingtalk.com/i/nodes/{node_id}")
        reject_folder_node(node, node_id, title)
    args.doc_metadata = node_markdown_metadata(node, args.url)
    args.current_node_id = node_id
    if extension not in {"adoc", "alidoc"}:
        if extension == "able":
            args.node_size = int(node.get("size") or 0)
            read_notable_base_to_csv(client, node_id, title, args)
            return 0
        if extension == "axls":
            read_workbook_to_csv(client, node_id, title, args)
            return 0
        return read_non_alidoc_file(client, args.url, node_id, title, extension, args)
    blocks_payload: dict[str, object] | None = None
    browser_fallback = False
    try:
        blocks_payload = cache.cached("blocks", {"docId": node_id}, lambda: client.read_blocks(node_id))
    except DingTalkError as exc:
        if args.format == "markdown" and should_use_browser_fallback(exc):
            browser_fallback = True
        else:
            raise
    if args.format == "json":
        if blocks_payload is None:
            raise DingTalkError("raw json output is unavailable when blocks API access is denied")
        print(json_dump(blocks_payload))
    else:
        args.source_url = args.url
        requested = set(args.with_parts or [])
        cached_path = cached_markdown_path(title, args, cache, node_id) if args.format == "markdown" and (bool(getattr(args, "output_path", False)) or "img-local" in requested) else None
        if cached_path is not None:
            print(json_dump({"outputPath": str(cached_path), "bytes": cached_path.stat().st_size, "chars": len(cached_path.read_text(encoding="utf-8")), "cached": True}))
            return 0
        if browser_fallback or requested.intersection({"img", "img-origin", "img-local", "diagram"}):
            content = private_markdown_with_session(
                args.url,
                default_browser_state_path().expanduser().resolve(),
                default_browser_wait_ms(),
                include_diagram="diagram" in requested,
            )
            if "img" in requested:
                content = proxify_markdown_images(content, args.proxy_port)
        elif blocks_payload is not None:
            content = blocks_to_markdown(markdown_title(title), blocks_payload)
        else:
            raise DingTalkError("document content is unavailable")
        emit_output(content, markdown_title(title), args)
    return 0


def cmd_assets(client: DingTalkClient, cache: Cache, args: argparse.Namespace) -> int:
    blocks_payload = cache.cached("blocks", {"docId": args.node_id}, lambda: client.read_blocks(args.node_id))
    assets = find_assets(blocks_payload)
    print(json_dump({"nodeId": args.node_id, "assetCount": len(assets), "assets": assets}))
    return 0


def cmd_cache(cache: Cache, args: argparse.Namespace) -> int:
    if args.cache_command == "stats":
        print(json_dump(cache.stats()))
        return 0
    if args.cache_command == "clear":
        deleted_files: list[str] = []
        output_paths = cache.output_paths() if args.namespace in (None, "output") else []
        if output_paths and not getattr(args, "yes", False):
            print(json_dump({
                "confirmationRequired": True,
                "message": "Clearing output cache deletes cached local output files. Rerun with --yes to confirm.",
                "files": [str(path) for path in output_paths],
                "namespace": args.namespace or "*",
            }))
            return 2
        for path in output_paths:
            for candidate in (path, sidecar_metadata_path(path)):
                if candidate.exists() and candidate.is_file():
                    candidate.unlink()
                    deleted_files.append(str(candidate))
        removed = cache.clear(args.namespace)
        print(json_dump({"path": str(cache.path), "removed": removed, "namespace": args.namespace or "*", "deletedFiles": deleted_files}))
        return 0
    raise DingTalkError(f"unknown cache command: {args.cache_command}")


def cmd_config_check(args: argparse.Namespace) -> int:
    helper = Path(args.helper).resolve()
    required = ["DINGTALK_APP_KEY", "DINGTALK_APP_SECRET", "DINGTALK_MY_USER_ID", "DINGTALK_MY_OPERATOR_ID"]
    values: dict[str, str] = {}
    for key in required:
        values[key] = helper_get_config(helper, key)
    auto_filled: list[str] = []
    if not values["DINGTALK_MY_OPERATOR_ID"]:
        converted = run_helper(helper, "--to-unionid").splitlines()[-1].strip()
        values["DINGTALK_MY_OPERATOR_ID"] = converted
        if converted:
            auto_filled.append("DINGTALK_MY_OPERATOR_ID")
    missing = [key for key in required if not values.get(key)]
    print(json_dump({
        "ok": not missing,
        "missing": missing,
        "autoFilled": auto_filled,
        "config": {key: mask_secret(values.get(key, "")) for key in required},
    }))
    return 0 if not missing else 2


def cmd_config(args: argparse.Namespace) -> int:
    helper = Path(args.helper).resolve()
    if args.config_command == "check":
        return cmd_config_check(args)
    if args.config_command == "get":
        lines = []
        for key in args.keys:
            value = config_get_value(key)
            lines.append(f"{key}={config_mask(key, value) if value else '（未设置）'}")
        print("\n".join(lines))
        return 0
    if args.config_command == "set":
        print(run_helper(helper, "--set", args.assignment))
        return 0
    if args.config_command == "to-unionid":
        helper_args = ["--to-unionid"]
        if args.user_id:
            helper_args.append(args.user_id)
        print(run_helper(helper, *helper_args).splitlines()[-1].strip())
        return 0
    raise DingTalkError(f"unknown config command: {args.config_command}")


def cmd_proxy(args: argparse.Namespace) -> int:
    proxy_migrate_json_links()
    raw_args = args.proxy_args or ["--help"]
    if raw_args and raw_args[0] == "serve":
        serve_parser = argparse.ArgumentParser(prog="cli.py proxy serve")
        serve_parser.add_argument("--port", type=int, required=True)
        serve_parser.add_argument("--browser-state", required=True)
        serve_args = serve_parser.parse_args(raw_args[1:])
        proxy_serve(serve_args.port, Path(serve_args.browser_state).expanduser().resolve())
        return 0
    proxy_parser = build_proxy_parser()
    proxy_args = proxy_parser.parse_args(raw_args)
    if proxy_args.proxy_command == "start":
        return cmd_proxy_start(proxy_args)
    if proxy_args.proxy_command == "status":
        return cmd_proxy_status(proxy_args)
    if proxy_args.proxy_command == "stop":
        return cmd_proxy_stop(proxy_args)
    if proxy_args.proxy_command == "shorten":
        return cmd_proxy_shorten(proxy_args)
    if proxy_args.proxy_command == "cleanup":
        return cmd_proxy_cleanup(proxy_args)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DingTalk knowledge search/read CLI for Coding Agents.")
    parser.add_argument("--helper", default=str(default_helper_path()), help=argparse.SUPPRESS)
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds before API calls")
    parser.add_argument("--cache", default=str(default_cache_path()), help="SQLite cache path")
    parser.add_argument("--cache-ttl", type=int, default=86400, help="Cache TTL seconds; <=0 disables expiry")
    parser.add_argument("--no-cache", action="store_true", help="Disable SQLite cache for this run")
    parser.add_argument("--asset-retention-days", type=int, default=0, help="Deprecated cleanup for legacy global asset directory; <=0 disables cleanup")
    parser.add_argument("--proxy-port", type=int, default=9697, help="Reserved fixed local proxy port for DingTalk resources")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config = subparsers.add_parser("config", help="Manage DingTalk skill configuration")
    config_subparsers = config.add_subparsers(dest="config_command", required=True)
    config_subparsers.add_parser("check", help="Validate required DingTalk skill configuration without printing secrets")
    config_get = config_subparsers.add_parser("get", help="Read config values with secret masking")
    config_get.add_argument("keys", nargs="+")
    config_set = config_subparsers.add_parser("set", help="Write one config value")
    config_set.add_argument("assignment", metavar="KEY=VALUE")
    config_union = config_subparsers.add_parser("to-unionid", help="Convert userId to unionId; defaults to configured current user")
    config_union.add_argument("user_id", nargs="?")
    search = subparsers.add_parser("search", help="Search DingTalk files/docs by keyword")
    search.add_argument("keyword")
    search.add_argument("--limit", type=int, default=10, help="Max results requested from API, capped at 50")
    search.add_argument("--concurrency", type=int, default=5, help="Max concurrent searches when keyword contains spaces, capped at 5")
    search.add_argument("--raw", action="store_true", help="Print raw API payload")

    read = subparsers.add_parser("read", help="Read a DingTalk document/file/AI table by alidocs URL or node id")
    read.add_argument("node_id", metavar="url_or_node_id")
    read.add_argument("--mode", choices=("file", "pdf2text"), default="file", help="file returns downloaded files as-is; pdf2text converts downloaded PDFs to .txt via pdftotext when available")
    read.add_argument("--format", choices=("markdown", "json"), default="markdown", help="Default markdown; json returns raw official blocks")
    read.add_argument("--with", dest="with_parts", action="append", choices=("img", "img-origin", "img-local", "diagram"), default=[], help="Enhance markdown output. img embeds local proxy URLs; img-origin embeds original DingTalk URLs; img-local downloads images; diagram embeds Mermaid/PlantUML code")
    read.add_argument("--source-url", help=argparse.SUPPRESS)
    read.add_argument("--assets-dir", default=str(default_assets_dir()), help="Legacy directory for standalone image downloads; --with img-local writes next to the markdown under .assets/<doc-name>/")
    read.add_argument("--output-dir", default=str(default_output_dir()), help="Directory for large markdown output files")
    read.add_argument("--output-strategy", choices=("link", "copy"), default="link", help="When output cache is hit, link cached files into output-dir by default; copy isolates the output file")
    read.add_argument("--output-cache-dir", default=str(default_output_cache_dir()), help=argparse.SUPPRESS)
    read.add_argument("--path-threshold", type=int, default=2000, help="Write markdown to file when content chars exceed this threshold")
    read.add_argument("--output-path", action="store_true", help="Always write markdown to file and return the path")
    read.add_argument("--all-sheets", action="store_true", help="Export all sheets for large AI tables; can be slow")
    read.add_argument("--sheet-confirm-threshold", type=int, default=10, help=argparse.SUPPRESS)
    read.add_argument("--large-table-threshold", type=int, default=50 * 1024 * 1024, help=argparse.SUPPRESS)
    read.add_argument("--resolve-title", action="store_true", help=argparse.SUPPRESS)

    assets = subparsers.add_parser("assets", help="Inspect image-like/attachment metadata in one document's blocks")
    assets.add_argument("node_id")

    resolve_url = subparsers.add_parser("resolve-url", help="Resolve an alidocs URL to DingTalk node metadata")
    resolve_url.add_argument("url")

    cache = subparsers.add_parser("cache", help="Inspect or clear the skill-local SQLite cache")
    cache_subparsers = cache.add_subparsers(dest="cache_command", required=True)
    cache_subparsers.add_parser("stats", help="Show cache entry counts")
    cache_clear = cache_subparsers.add_parser("clear", help="Clear cache entries")
    cache_clear.add_argument("--namespace", choices=("node", "resolve-url", "blocks", "output"), help="Only clear one namespace")
    cache_clear.add_argument("--yes", action="store_true", help="Confirm deletion. Required when clearing cached output files")

    subparsers.add_parser("proxy", help="Manage the local DingTalk resource proxy")

    login = subparsers.add_parser("login", help="Start or verify DingTalk QR login")
    login.add_argument("url", nargs="?", default="https://alidocs.dingtalk.com/", help="DingTalk/alidocs URL to open for login when no login session is active")
    login.add_argument("--url", dest="url_option", help="DingTalk/alidocs URL to open for login")
    browser = subparsers.add_parser("browser", help="Manage skill-owned browser sessions")
    browser_subparsers = browser.add_subparsers(dest="browser_command", required=True)
    browser_close = browser_subparsers.add_parser("close", help="Close skill-owned browser sessions and force-kill leftovers")
    browser_close.add_argument("--force", action="store_true", help="Also pkill leftover agent-browser/chrome processes")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    actual_argv = sys.argv[1:] if argv is None else argv
    if not actual_argv:
        parser.print_help()
        return 0
    if actual_argv[0] == "proxy":
        return cmd_proxy(argparse.Namespace(proxy_args=actual_argv[1:]))
    args = parser.parse_args(actual_argv)
    if args.command == "config":
        return cmd_config(args)
    if args.command == "browser" and args.browser_command == "close":
        if args.force:
            remaining = close_agent_browser_force()
            print(json_dump({"closed": not remaining, "remaining": remaining}))
        else:
            run_agent_browser(["close"], timeout=120)
        return 0
    cache = Cache(Path(args.cache).resolve(), enabled=not args.no_cache, ttl_seconds=args.cache_ttl)
    if args.command == "cache":
        return cmd_cache(cache, args)
    client = DingTalkClient(DingTalkAuth(Path(args.helper).resolve()), sleep_seconds=args.sleep)
    cleanup_old_assets(Path(getattr(args, "assets_dir", str(default_assets_dir()))).expanduser().resolve(), args.asset_retention_days)
    if args.command == "search":
        return cmd_search(client, cache, args)
    if args.command == "read":
        args.cache = cache
        return cmd_read(client, cache, args)
    if args.command == "assets":
        return cmd_assets(client, cache, args)
    if args.command == "resolve-url":
        return cmd_resolve_url(client, cache, args)
    if args.command == "login":
        return cmd_login(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LoginRequired as exc:
        print(json_dump(exc.payload))
        raise SystemExit(2)
    except DingTalkError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
