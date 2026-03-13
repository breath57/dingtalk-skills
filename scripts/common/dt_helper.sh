#!/bin/bash
# =============================================================================
# dt_helper.sh — 钉钉开放平台辅助工具
# 路径: scripts/common/dt_helper.sh
# 用法: bash scripts/common/dt_helper.sh <命令> [参数]
# =============================================================================

set -e

CONFIG="${DINGTALK_CONFIG:-$HOME/.dingtalk-skills/config}"

# ─────────────────────────────────────────────────────────────────────────────
# 帮助信息
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
  cat <<'EOF'
钉钉开放平台辅助工具 (dt_helper.sh)
用法: bash scripts/common/dt_helper.sh <命令> [参数]

Token 管理（两种 token 互不兼容，按域名区分）：
  --token [--nocache]  获取新版 accessToken（用于 api.dingtalk.com 域名的所有接口）
                       适用：待办、文档、AI 表格等 api.dingtalk.com 域名下所有版本的接口
                       请求头：x-acs-dingtalk-access-token: <token>
                       有缓存且未过期则直接返回，否则自动刷新并缓存
                       --nocache：跳过缓存，强制重新获取（token 被提前吊销时使用）
  --token-info         查看新版 token 缓存状态（是否有效、剩余有效秒数）
  --clear-token        清除缓存的新版 token（下次 --token 时强制重新获取）
  --old-token [--nocache]
                       获取旧版 access_token（用于 oapi.dingtalk.com 域名的所有接口）
                       适用：群消息/工作通知/userId↔unionId 转换等 oapi.dingtalk.com 接口
                       不适用：api.dingtalk.com 接口（如待办、文档、AI表格）
                       ⚠️  新旧两种 token 互不兼容，混用会导致 401/403
                       --nocache：跳过缓存，强制重新获取（token 被提前吊销时使用）

身份转换：
  --to-unionid [userId]   将 userId 转换为 unionId
                          不传参数：转换配置中的 DINGTALK_MY_USER_ID（操作者自身），
                                    结果首次自动写入 DINGTALK_MY_OPERATOR_ID
                          传入参数：动态转换指定 userId，仅返回结果，不写入配置
  --to-userid  [unionId]  将 unionId 反向转换为 userId（需传入参数）

配置管理：
  --config             查看 ~/.dingtalk-skills/config 中的所有配置项（敏感项脱敏显示）
  --get  KEY [KEY...]  获取一个或多个配置项的值（敏感项脱敏显示）
  --set  KEY=VALUE     将配置项持久化写入配置文件（已存在则更新，不存在则追加，目录自动创建）

帮助：
  --help, -h           显示此帮助信息

环境变量：
  DINGTALK_CONFIG      覆盖默认配置文件路径（默认 ~/.dingtalk-skills/config）

配置文件：
  ~/.dingtalk-skills/config   key=value 格式，存储以下键：
    DINGTALK_APP_KEY           应用 Client ID（AppKey）
    DINGTALK_APP_SECRET        应用 Client Secret（AppSecret）
    DINGTALK_MY_USER_ID           企业员工 ID（userId，管理后台通讯录可查）
    DINGTALK_MY_OPERATOR_ID       操作者 unionId（由 --to-unionid 自动生成）
    DINGTALK_ACCESS_TOKEN      新版 token 缓存
    DINGTALK_TOKEN_EXPIRY      新版 token 过期时间戳（Unix 秒）
    DINGTALK_OLD_TOKEN         旧版 token 缓存
    DINGTALK_OLD_TOKEN_EXPIRY  旧版 token 过期时间戳（Unix 秒）

EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────

# 从配置文件读取指定键的值
cfg_get() {
  local key="$1"
  grep "^${key}=" "$CONFIG" 2>/dev/null | head -1 | cut -d= -f2-
}

# 写入或更新配置文件中的键值
cfg_set() {
  local key="$1"
  local value="$2"
  mkdir -p "$(dirname "$CONFIG")"
  touch "$CONFIG"
  if grep -q "^${key}=" "$CONFIG" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$CONFIG"
  else
    echo "${key}=${value}" >> "$CONFIG"
  fi
}

# 从配置文件删除指定键
cfg_del() {
  local key="$1"
  sed -i "/^${key}=/d" "$CONFIG" 2>/dev/null || true
}

# 确保必须的配置项存在，否则报错退出
require_cfg() {
  local key="$1"
  local val
  val=$(cfg_get "$key")
  if [ -z "$val" ]; then
    echo "❌ 缺少配置项 ${key}，请先运行: bash scripts/common/dt_helper.sh --set ${key}=<值>" >&2
    exit 1
  fi
  echo "$val"
}

# ─────────────────────────────────────────────────────────────────────────────
# Token 管理
# ─────────────────────────────────────────────────────────────────────────────

cmd_token() {
  local force="${1:-}" app_key app_secret cached expiry now resp token expire_in

  app_key=$(require_cfg DINGTALK_APP_KEY)
  app_secret=$(require_cfg DINGTALK_APP_SECRET)
  now=$(date +%s)

  if [ "$force" != "--nocache" ]; then
    cached=$(cfg_get DINGTALK_ACCESS_TOKEN)
    expiry=$(cfg_get DINGTALK_TOKEN_EXPIRY)
    if [ -n "$cached" ] && [ -n "$expiry" ] && [ "$now" -lt "$expiry" ]; then
      echo "$cached"
      return 0
    fi
  fi

  # 过期或无缓存，重新获取
  resp=$(curl -s -X POST "https://api.dingtalk.com/v1.0/oauth2/accessToken" \
    -H "Content-Type: application/json" \
    -d "{\"appKey\":\"${app_key}\",\"appSecret\":\"${app_secret}\"}")

  token=$(echo "$resp" | grep -o '"accessToken":"[^"]*"' | cut -d'"' -f4)
  expire_in=$(echo "$resp" | grep -o '"expireIn":[0-9]*' | cut -d: -f2)

  if [ -z "$token" ]; then
    echo "❌ 获取 token 失败: $resp" >&2
    exit 1
  fi

  cfg_set DINGTALK_ACCESS_TOKEN "$token"
  cfg_set DINGTALK_TOKEN_EXPIRY "$((now + expire_in - 200))"

  echo "$token"
}

cmd_token_info() {
  local cached expiry now remaining

  cached=$(cfg_get DINGTALK_ACCESS_TOKEN)
  expiry=$(cfg_get DINGTALK_TOKEN_EXPIRY)
  now=$(date +%s)

  if [ -z "$cached" ]; then
    echo "状态: 无缓存（从未获取或已清除）"
    return 0
  fi

  if [ -z "$expiry" ] || [ "$now" -ge "$expiry" ]; then
    echo "状态: 已过期"
    echo "Token: ${cached:0:20}..."
  else
    remaining=$((expiry - now))
    echo "状态: 有效"
    echo "Token: ${cached:0:20}..."
    echo "剩余: ${remaining} 秒（约 $((remaining / 60)) 分钟）"
  fi
}

cmd_clear_token() {
  cfg_del DINGTALK_ACCESS_TOKEN
  cfg_del DINGTALK_TOKEN_EXPIRY
  echo "✅ 新版 Token 缓存已清除"
}

cmd_old_token() {
  # 旧版 access_token，用于所有 oapi.dingtalk.com 接口：
  #   - 群消息、工作通知、互动卡片（dingtalk-message）
  #   - userId ↔ unionId 转换
  # ⚠️  不可用于 api.dingtalk.com 接口（待办、文档、AI表格等）
  local force="${1:-}" app_key app_secret resp token cached expiry now

  app_key=$(require_cfg DINGTALK_APP_KEY)
  app_secret=$(require_cfg DINGTALK_APP_SECRET)
  now=$(date +%s)

  if [ "$force" != "--nocache" ]; then
    cached=$(cfg_get DINGTALK_OLD_TOKEN)
    expiry=$(cfg_get DINGTALK_OLD_TOKEN_EXPIRY)
    if [ -n "$cached" ] && [ -n "$expiry" ] && [ "$now" -lt "$expiry" ]; then
      echo "$cached"
      return 0
    fi
  fi

  resp=$(curl -s "https://oapi.dingtalk.com/gettoken?appkey=${app_key}&appsecret=${app_secret}")
  token=$(echo "$resp" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
  expires_in=$(echo "$resp" | grep -o '"expires_in":[0-9]*' | cut -d: -f2)

  if [ -z "$token" ]; then
    echo "❌ 获取旧版 token 失败: $resp" >&2
    exit 1
  fi

  cfg_set DINGTALK_OLD_TOKEN "$token"
  cfg_set DINGTALK_OLD_TOKEN_EXPIRY "$((now + expires_in - 200))"

  echo "$token"
}

# ─────────────────────────────────────────────────────────────────────────────
# 身份转换
# ─────────────────────────────────────────────────────────────────────────────

cmd_to_unionid() {
  local user_id="$1"
  local is_self=false
  local old_token resp union_id

  # 未传参 → 使用配置中的操作者自身 userId，转换结果写入配置
  if [ -z "$user_id" ]; then
    user_id=$(require_cfg DINGTALK_MY_USER_ID)
    is_self=true
  fi

  old_token=$(cmd_old_token)

  resp=$(curl -s -X POST \
    "https://oapi.dingtalk.com/topapi/v2/user/get?access_token=${old_token}" \
    -H "Content-Type: application/json" \
    -d "{\"userid\":\"${user_id}\"}")

  # 注意：使用无下划线的 unionid 字段（有下划线的 union_id 可能为空）
  union_id=$(echo "$resp" | grep -o '"unionid":"[^"]*"' | head -1 | cut -d'"' -f4)

  if [ -z "$union_id" ]; then
    echo "❌ userId→unionId 转换失败: $resp" >&2
    exit 1
  fi

  # 仅当转换的是操作者自身时，才写入配置（动态转换他人 userId 不写入）
  if "$is_self" && [ -z "$(cfg_get DINGTALK_MY_OPERATOR_ID)" ]; then
    cfg_set DINGTALK_MY_OPERATOR_ID "$union_id"
    echo "✅ 自身 unionId 已写入配置 DINGTALK_MY_OPERATOR_ID" >&2
  fi

  echo "$union_id"
}

cmd_to_userid() {
  local union_id="$1"
  local old_token resp user_id

  if [ -z "$union_id" ]; then
    echo "❌ 请提供 unionId 参数" >&2
    exit 1
  fi

  old_token=$(cmd_old_token)

  resp=$(curl -s -X POST \
    "https://oapi.dingtalk.com/topapi/user/getbyunionid?access_token=${old_token}" \
    -H "Content-Type: application/json" \
    -d "{\"unionid\":\"${union_id}\"}")

  user_id=$(echo "$resp" | grep -o '"userid":"[^"]*"' | head -1 | cut -d'"' -f4)

  if [ -z "$user_id" ]; then
    echo "❌ unionId→userId 转换失败: $resp" >&2
    exit 1
  fi

  echo "$user_id"
}

# ─────────────────────────────────────────────────────────────────────────────
# 配置管理
# ─────────────────────────────────────────────────────────────────────────────

cmd_config() {
  if [ ! -f "$CONFIG" ]; then
    echo "配置文件不存在: $CONFIG"
    echo "使用 --set KEY=VALUE 写入配置项"
    return 0
  fi

  echo "配置文件: $CONFIG"
  echo "─────────────────────────────────"
  # 脱敏显示 SECRET 和 TOKEN
  while IFS= read -r line; do
    key="${line%%=*}"
    val="${line#*=}"
    case "$key" in
      DINGTALK_APP_SECRET|DINGTALK_ACCESS_TOKEN|DINGTALK_OLD_TOKEN)
        echo "${key}=${val:0:6}***（已脱敏）"
        ;;
      *)
        echo "$line"
        ;;
    esac
  done < "$CONFIG"
}

cmd_get() {
  if [ $# -eq 0 ]; then
    echo "❌ 请提供至少一个键名，用法: --get KEY [KEY2 ...]" >&2
    exit 1
  fi
  for key in "$@"; do
    val=$(cfg_get "$key")
    if [ -z "$val" ]; then
      echo "${key}=（未设置）"
    else
      case "$key" in
        DINGTALK_APP_SECRET|DINGTALK_ACCESS_TOKEN|DINGTALK_OLD_TOKEN)
          echo "${key}=${val:0:6}***（脱敏）"
          ;;
        *)
          echo "${key}=${val}"
          ;;
      esac
    fi
  done
}

cmd_set() {
  local kv="$1"
  if [ -z "$kv" ] || [[ "$kv" != *"="* ]]; then
    echo "❌ 格式错误，用法: --set KEY=VALUE" >&2
    exit 1
  fi
  local key="${kv%%=*}"
  local value="${kv#*=}"
  cfg_set "$key" "$value"
  echo "✅ 已设置 ${key}"
}

# ─────────────────────────────────────────────────────────────────────────────
# 入口：解析命令
# ─────────────────────────────────────────────────────────────────────────────

CMD="${1:-}"

case "$CMD" in
  --help|-h|"")
    show_help
    ;;
  --token)
    cmd_token "${2:-}"
    ;;
  --token-info)
    cmd_token_info
    ;;
  --clear-token)
    cmd_clear_token
    ;;
  --old-token)
    cmd_old_token "${2:-}"
    ;;
  --to-unionid)
    cmd_to_unionid "${2:-}"
    ;;
  --to-userid)
    cmd_to_userid "${2:-}"
    ;;
  --config)
    cmd_config
    ;;
  --get)
    shift
    cmd_get "$@"
    ;;
  --set)
    cmd_set "${2:-}"
    ;;
  *)
    echo "❌ 未知命令: $CMD" >&2
    echo "运行 --help 查看用法" >&2
    exit 1
    ;;
esac
