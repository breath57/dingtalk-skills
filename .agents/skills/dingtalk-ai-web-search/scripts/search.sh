#!/usr/bin/env bash
# web_search_v3/scripts/search.sh
# 网页搜索脚本（小宿智能搜索 MCP 网关）
# 依赖：curl（+ bash/grep/sed 等标准系统工具，无需任何 npm install / pip install）
#
# 用法：
#   bash search.sh -q "搜索词" [选项]
#
# 选项：
#   -q, --query      搜索词（正常搜索时必填）
#   -c, --config     MCP JSON 配置字符串（配合 --save 使用）
#   -n, --count      返回条数（默认: 5，最大 50）
#   -f, --freshness  noLimit|oneDay|oneWeek|oneMonth|oneYear（默认: noLimit）
#   --json           以 JSON 格式输出
#   --ping           仅测试连通性，列出可用工具后退出
#   --save           对 -c 指定的配置做连通性测试，通过后永久写入本脚本

set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/$(basename "${BASH_SOURCE[0]}")"

# JSON 解析工具优先级：jq > python3/python > bare grep
JQ=""
command -v jq &>/dev/null && JQ=jq

PYTHON=""
if command -v python3 &>/dev/null; then
  PYTHON=python3
elif command -v python &>/dev/null; then
  PYTHON=python
fi

# 配置文件路径（URL 存储在脚本旁边，不自修改脚本本身）
CONFIG_FILE="$(dirname "$SCRIPT_PATH")/.mcp_url"
DEFAULT_MCP_URL=""
[[ -f "$CONFIG_FILE" ]] && DEFAULT_MCP_URL="$(cat "$CONFIG_FILE")" || true

# ── 工具函数 ──────────────────────────────────────────────────────────────────

die()  { echo "错误：$*" >&2; exit 1; }

# JSON 字符串转义（bash 内建，无外部依赖）
json_str() {
  local s="$1"
  s="${s//\\/\\\\}"       # \ → \\
  s="${s//\"/\\\"}"       # " → \"
  s="${s//$'\n'/\\n}"     # newline
  s="${s//$'\r'/\\r}"     # CR
  s="${s//$'\t'/\\t}"     # tab
  printf '"%s"' "$s"
}

# 保存 URL 到配置文件（不修改脚本本身，彻底避免 bash 缓冲读取问题）
save_url() {
  local url="$1"
  printf '%s' "$url" > "$CONFIG_FILE" || die "写入配置文件失败，请检查文件权限（$CONFIG_FILE）"
}

# 解析 MCP JSON 配置，提取 url 字段
parse_mcp_url() {
  local cfg="$1"
  if [[ -n "$JQ" ]]; then
    echo "$cfg" | jq -re '[.mcpServers[].url] | first' 2>/dev/null \
      || die "配置中未找到有效的 url 字段，请确认 JSON 格式正确"
  elif [[ -n "$PYTHON" ]]; then
    $PYTHON -c "
import sys, json
try:
    cfg = json.loads(sys.argv[1])
    for srv in cfg.get('mcpServers', {}).values():
        if srv.get('url'):
            print(srv['url'])
            sys.exit(0)
    sys.exit(1)
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
" "$cfg" || die "配置中未找到有效的 url 字段，请确认 JSON 格式正确"
  else
    echo "$cfg" \
      | grep -o '"url"[[:space:]]*:[[:space:]]*"[^"]*"' \
      | head -1 \
      | sed 's/"url"[[:space:]]*:[[:space:]]*"//;s/"$//' \
      || die "配置中未找到有效的 url 字段"
  fi
}

# ── MCP Streamable HTTP 请求 ──────────────────────────────────────────────────

# 发送 MCP POST，返回响应 JSON（自动处理 SSE）
# 用法: mcp_post <url> <body> [session_id]
mcp_post() {
  local url="$1" body="$2" sid="${3:-}"
  local hdr_file ct resp

  hdr_file=$(mktemp) || die "无法创建临时文件"

  local -a cmd=(
    curl -s -S -m 30 --connect-timeout 10
    -X POST
    -H 'Content-Type: application/json'
    -H 'Accept: application/json, text/event-stream'
    -D "$hdr_file"
    --data-raw "$body"
  )
  [[ -n "$sid" ]] && cmd+=(-H "Mcp-Session-Id: $sid")
  cmd+=("$url")

  if ! resp=$("${cmd[@]}" 2>&1); then
    rm -f "$hdr_file"
    die "$resp"
  fi

  ct=$(grep -i '^content-type:' "$hdr_file" | tail -1 \
       | tr -d '\r\n' | sed 's/^[Cc]ontent-[Tt]ype:[[:space:]]*//' || true)
  rm -f "$hdr_file"

  if [[ "$ct" == *event-stream* ]]; then
    # 从 SSE 流中取最后一条含 result / error 的 data 行
    resp=$(printf '%s\n' "$resp" \
           | grep '^data: ' \
           | grep -E '"result"|"error"' \
           | tail -1 \
           | cut -c7-)
  fi

  printf '%s\n' "$resp"
}

# 初始化 MCP 会话，输出 Session-ID（可为空）
mcp_init() {
  local url="$1"
  local hdr_file
  hdr_file=$(mktemp) || die "无法创建临时文件"

  curl -s -S -m 30 --connect-timeout 10 \
    -X POST \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -D "$hdr_file" \
    --data-raw '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"web-search","version":"1.0.0"}}}' \
    "$url" > /dev/null 2>&1 || true

  grep -i '^mcp-session-id:' "$hdr_file" \
    | tr -d '\r\n' \
    | sed 's/^[Mm][Cc][Pp]-[Ss]ession-[Ii][Dd]:[[:space:]]*//' \
    || true
  rm -f "$hdr_file"
}

# 提取 JSON-RPC 错误消息（有错误时输出，否则空）
rpc_error() {
  echo "$1" | grep -o '"message":"[^"]*"' | head -1 \
    | sed 's/"message":"//;s/"$//' || true
}

# ── 命令实现 ──────────────────────────────────────────────────────────────────

cmd_ping() {
  local url="$1"
  local sid resp tools

  sid=$(mcp_init "$url")
  mcp_post "$url" \
    '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
    "$sid" > /dev/null 2>&1 || true

  resp=$(mcp_post "$url" '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' "$sid")

  if echo "$resp" | grep -q '"error"'; then
    local msg; msg=$(rpc_error "$resp")
    die "连接失败：${msg:-未知错误}"
  fi

  if [[ -n "$JQ" ]]; then
    tools=$(echo "$resp" | jq -r '[.result.tools[].name] | join(", ")' 2>/dev/null || echo "（无法解析）")
  elif [[ -n "$PYTHON" ]]; then
    tools=$($PYTHON -c "
import sys, json
d = json.loads(sys.argv[1])
names = [t['name'] for t in d.get('result', {}).get('tools', [])]
print(', '.join(names) if names else '（无工具）')
" "$resp")
  else
    tools=$(echo "$resp" \
            | grep -o '"name":"[^"]*"' \
            | sed 's/"name":"//;s/"$//' \
            | tr '\n' ',' | sed 's/,$//' || echo "（无法解析）")
  fi

  echo "✓ 连通成功，可用工具：$tools"
}

cmd_search() {
  local url="$1" query="$2" count="${3:-5}" freshness="${4:-noLimit}" as_json="${5:-false}"

  # freshness 映射
  local fv=""
  case "$freshness" in
    oneDay)   fv="Day" ;;
    oneWeek)  fv="Week" ;;
    oneMonth) fv="Month" ;;
    oneYear)  fv="Year" ;;
  esac

  # 构建 tool_arguments JSON
  local q_json; q_json=$(json_str "$query")
  local tool_args="{\"q\":${q_json},\"count\":${count}"
  [[ -n "$fv" ]] && tool_args+=",\"freshness\":\"${fv}\""
  tool_args+="}"

  local call_body
  call_body="{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"web_search\",\"arguments\":${tool_args}}}"

  # 初始化会话
  local sid
  sid=$(mcp_init "$url")
  mcp_post "$url" \
    '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
    "$sid" > /dev/null 2>&1 || true

  # 调用工具
  local resp
  resp=$(mcp_post "$url" "$call_body" "$sid")

  if echo "$resp" | grep -q '"error"'; then
    local msg; msg=$(rpc_error "$resp")
    die "搜索失败：${msg:-未知错误}"
  fi

  # 提取 content[0].text
  local text
  if [[ -n "$JQ" ]]; then
    text=$(echo "$resp" | jq -r '.result.content[0].text' 2>/dev/null) || die "无法解析搜索结果"
  elif [[ -n "$PYTHON" ]]; then
    text=$($PYTHON -c "
import sys, json
d = json.loads(sys.argv[1])
print(d['result']['content'][0]['text'])
" "$resp") || die "无法解析搜索结果"
  else
    # grep -P 处理 JSON 转义字符串（GNU grep）；失败则输出原始响应
    # 正则 (\\.|[^"])* 匹配：\"（转义引号）或任意非引号字符
    text=$(echo "$resp" \
           | grep -oP '"text":"\K(\\.|[^"])*' \
           | head -1 \
           | sed 's/\\"/"/g;s/\\\\/\\/g' 2>/dev/null) || text=""
  fi

  # 格式化并输出结果
  if [[ -n "$JQ" ]]; then
    if $as_json; then
      echo "$text" | jq -r '
        [ .webPages.value[]? // .result.webPages.value[]? | {
            title: (.name // .title // ""),
            url: (.url // ""),
            snippet: ((.snippet // .summary // "")[:300]),
            site: (.siteName // ""),
            published: ((.datePublished // "")[:10]),
            source: "小宿智能搜索"
        }] ' 2>/dev/null || echo "$text"
    else
      echo "$text" | jq -r '
        (.webPages.value // .result.webPages.value // []) | to_entries[] |
        "[\(.key + 1)] \(.value.name // .value.title // "")\n    URL: \(.value.url // "")\n    摘要: \((.value.snippet // .value.summary // "")[:200])\n"' \
        2>/dev/null || echo "$text"
    fi
  elif [[ -n "$PYTHON" ]]; then
    $PYTHON -c "
import sys, json

text    = sys.argv[1]
as_json = sys.argv[2] == 'true'

try:
    data = json.loads(text)
except Exception:
    print(text)
    sys.exit(0)

pages = data.get('webPages', {}).get('value', [])
if not pages:
    pages = data.get('result', {}).get('webPages', {}).get('value', [])
if not pages:
    print(text[:1000] if not as_json else json.dumps({'raw': text[:1000]}, ensure_ascii=False))
    sys.exit(0)

if as_json:
    out = []
    for p in pages:
        out.append({
            'title':     p.get('name') or p.get('title', ''),
            'url':       p.get('url', ''),
            'snippet':   (p.get('snippet') or p.get('summary', ''))[:300],
            'site':      p.get('siteName', ''),
            'published': (p.get('datePublished') or '')[:10],
            'source':    '小宿智能搜索',
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))
else:
    for i, p in enumerate(pages, 1):
        title   = p.get('name') or p.get('title', '')
        url     = p.get('url', '')
        snippet = (p.get('snippet') or p.get('summary', ''))[:200]
        site    = p.get('siteName', '')
        pub     = (p.get('datePublished') or '')[:10]
        print(f'[{i}] {title}')
        if url:     print(f'    URL: {url}')
        if snippet: print(f'    摘要: {snippet}')
        if site:    print(f'    来源: {site}  (小宿智能搜索)')
        if pub:     print(f'    发布: {pub}')
        print()
" "$text" "$as_json"
  else
    # 最终兜底：输出原始文本，提示安装 python 或 jq
    echo "(提示：安装 python 或 jq 可获得格式化输出，当前输出原始结果)" >&2
    echo "$text"
  fi
}

# ── 主函数（包裹全部逻辑，bash 定义函数时整体读入内存，避免自写文件时触发 EOF）──

main() {
  local ARG_QUERY="" ARG_CONFIG="" ARG_COUNT=5
  local ARG_FRESHNESS="noLimit" ARG_JSON=false ARG_PING=false ARG_SAVE=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -q|--query)     ARG_QUERY="$2";      shift 2 ;;
      -c|--config)    ARG_CONFIG="$2";     shift 2 ;;
      -n|--count)     ARG_COUNT="$2";      shift 2 ;;
      -f|--freshness) ARG_FRESHNESS="$2";  shift 2 ;;
      --json)         ARG_JSON=true;       shift   ;;
      --ping)         ARG_PING=true;       shift   ;;
      --save)         ARG_SAVE=true;       shift   ;;
      *) die "未知参数：$1（使用 -q/--query、--ping、--save 等）" ;;
    esac
  done

  if $ARG_SAVE; then
    [[ -z "$ARG_CONFIG" ]] && die "--save 需要配合 -c 传入 MCP JSON 配置"
    local MCP_URL
    MCP_URL=$(parse_mcp_url "$ARG_CONFIG")
    echo "正在检测连通性..."
    cmd_ping "$MCP_URL"
    save_url "$MCP_URL"
    echo "✓ 配置已保存，后续调用无需再传 -c 参数。" >&2

  elif $ARG_PING; then
    [[ -z "$DEFAULT_MCP_URL" ]] && die "未配置 MCP URL，请先使用 --save 完成配置"
    cmd_ping "$DEFAULT_MCP_URL"

  else
    [[ -z "$ARG_QUERY" ]]       && die "请使用 -q 指定搜索词"
    [[ -z "$DEFAULT_MCP_URL" ]] && die "未配置 MCP URL，请先使用 --save 完成配置"
    cmd_search "$DEFAULT_MCP_URL" "$ARG_QUERY" "$ARG_COUNT" "$ARG_FRESHNESS" "$ARG_JSON"
  fi
}

main "$@"
