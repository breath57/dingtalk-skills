# DingTalk Login State

## Normal Flow

- Prefer API reads for normal documents.
- Use browser fallback only when `--with img-local`, `--with diagram`, or API `403 forbidden.accessDenied` requires rendered web content.
- The browser fallback first tries the saved `agent-browser` state.
- If DingTalk redirects to `login.dingtalk.com`, run `login` to open the page, wait until the QR image/canvas is rendered, capture the QR element as a screenshot under the current project's `.skills-workspace/dingtalk-knowledge-search/`, print the screenshot path, and exit immediately.
- Give the screenshot to the user to scan in DingTalk.
- After the user scans, run the same `login` command again. If the target DingTalk document opens and an iframe is loaded, the script saves `$HOME/.dingtalk-skills/dingtalk-knowledge-search/dingtalk-browser-state.json` and closes the login session.
- Subsequent reads use the saved state and return to background/headless operation.

## QR Screenshot Login

- The login screenshot is written as `.skills-workspace/dingtalk-knowledge-search/*-login-qr.png` in the current project by default.
- Set `DINGTALK_LOGIN_SCREENSHOT_DIR` to override the screenshot directory.
- The screenshot targets the QR element itself when possible, not the full login page.
- The `login` command prints JSON with `action: "scan_required"` and `screenshotPath` when a QR scan is needed.
- It must see both QR-login text and a rendered QR image/canvas/background before it captures the screenshot.
- The same `login` command prints `action: "authenticated"` after successful scan and state save.
- Login is considered usable only after the page URL is under `https://alidocs.dingtalk.com/` and the document iframe exists.
- No `xdotool`, desktop coordinate click, or headed browser interaction is required for the normal QR flow.
- Browser-backed reads that discover an expired/missing login state run the same QR screenshot flow and return JSON with `loginRequired: true` and `screenshotPath` instead of blocking for scan.

## Manual Recovery

Manual login flow:

```bash
python3 cli.py login "https://alidocs.dingtalk.com/i/nodes/<node_id>"
python3 cli.py login "https://alidocs.dingtalk.com/i/nodes/<node_id>"
```

The user scans the screenshot with DingTalk between those commands. After the document opens, the second `login` saves `$HOME/.dingtalk-skills/dingtalk-knowledge-search/dingtalk-browser-state.json` and closes the login session.

## Force Closing agent-browser

Normally close with:

```bash
python3 cli.py browser close
```

If `agent-browser` reports stale daemon/session behavior, force close only agent-browser-owned processes:

```bash
python3 cli.py browser close --force
```

Equivalent manual checks:

```bash
pgrep -af "agent-browser|/tmp/agent-browser-chrome-|chrome_crashpad_handler"
ss -ltnp
```

Avoid broad `pkill chrome`; it may kill the user's unrelated browser.
