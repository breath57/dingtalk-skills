#!/bin/bash
# =============================================================================
# test_dt_helper.sh — dt_helper.sh 功能测试
# 用法: bash tests/test_dt_helper.sh
# 前置: tests/.env 已配置（凭证从 .env 自动读取，不依赖 ~/.dingtalk-skills/config）
# =============================================================================

set -e

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TESTS_DIR/.." && pwd)"
HELPER="$REPO_ROOT/scripts/common/dt_helper.sh"
ENV_FILE="$TESTS_DIR/.env"

# ─────────────────────────────────────────────────────────────────────────────
# 从 tests/.env 读取凭证，写入临时 config，测试结束后自动清理
# ─────────────────────────────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ 找不到 $ENV_FILE，请先配置测试凭证" >&2
  exit 1
fi

load_env() {
  local key="$1"
  grep "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-
}

DINGTALK_APP_KEY=$(load_env DINGTALK_APP_KEY)
DINGTALK_APP_SECRET=$(load_env DINGTALK_APP_SECRET)
# .env 中 OPERATOR_ID 即 MY_OPERATOR_ID（unionId），TEST_USER_ID 即 MY_USER_ID（userId）
DINGTALK_MY_USER_ID=$(load_env DINGTALK_MY_USER_ID)
DINGTALK_MY_OPERATOR_ID=$(load_env OPERATOR_ID)

if [ -z "$DINGTALK_APP_KEY" ] || [ -z "$DINGTALK_APP_SECRET" ]; then
  echo "❌ tests/.env 缺少 DINGTALK_APP_KEY 或 DINGTALK_APP_SECRET" >&2
  exit 1
fi

# 使用临时 config，隔离测试与真实配置
TEMP_CONFIG=$(mktemp /tmp/dt_helper_test_config.XXXXXX)
export DINGTALK_CONFIG="$TEMP_CONFIG"

cat > "$TEMP_CONFIG" <<EOF
DINGTALK_APP_KEY=${DINGTALK_APP_KEY}
DINGTALK_APP_SECRET=${DINGTALK_APP_SECRET}
EOF
[ -n "$DINGTALK_MY_USER_ID" ]    && echo "DINGTALK_MY_USER_ID=${DINGTALK_MY_USER_ID}"    >> "$TEMP_CONFIG"
[ -n "$DINGTALK_MY_OPERATOR_ID" ] && echo "DINGTALK_MY_OPERATOR_ID=${DINGTALK_MY_OPERATOR_ID}" >> "$TEMP_CONFIG"

cleanup() { rm -f "$TEMP_CONFIG"; }
trap cleanup EXIT

pass=0
fail=0
skip=0

# ─────────────────────────────────────────────────────────────────────────────
# 测试工具函数
# ─────────────────────────────────────────────────────────────────────────────

ok() {
  echo "  ✅ $1"
  pass=$((pass + 1))
}

ng() {
  echo "  ❌ $1"
  echo "     期望: $2"
  echo "     实际: $3"
  fail=$((fail + 1))
}

sk() {
  echo "  ⏭️  $1（跳过: $2）"
  skip=$((skip + 1))
}

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -qF -- "$needle"; then
    ok "$desc"
  else
    ng "$desc" "包含: $needle" "$(echo "$haystack" | head -3)..."
  fi
}

assert_exit_nonzero() {
  local desc="$1"
  shift
  if ! "$@" >/dev/null 2>&1; then
    ok "$desc"
  else
    ng "$desc" "退出码非0" "退出码=0"
  fi
}

require_config() {
  local key="$1"
  local val
  val=$(grep "^${key}=" "$DINGTALK_CONFIG" 2>/dev/null | cut -d= -f2-)
  if [ -z "$val" ]; then
    echo "skip"
  else
    echo "$val"
  fi
}

echo "================================================================="
echo " dt_helper.sh 功能测试"
echo " 脚本路径: $HELPER"
echo "================================================================="

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "【1】帮助信息"
# ─────────────────────────────────────────────────────────────────────────────

out=$(bash "$HELPER" --help)
assert_contains "--help 输出包含 --token"       "--token"       "$out"
assert_contains "--help 输出包含 --old-token"   "--old-token"   "$out"
assert_contains "--help 输出包含 --to-unionid"  "--to-unionid"  "$out"
assert_contains "--help 输出包含 --get"         "--get"         "$out"
assert_contains "--help 输出包含 --set"         "--set"         "$out"
assert_contains "--help 输出包含 --init"        "--init"        "$out"

# 无参数也应显示帮助，exit 0
out2=$(bash "$HELPER")
assert_contains "无参数输出帮助" "--token" "$out2"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "【2】配置读写（--set / --get / --config）"
# ─────────────────────────────────────────────────────────────────────────────

# 写入测试键
bash "$HELPER" --set _DT_TEST_KEY=hello123 >/dev/null
out=$(bash "$HELPER" --get _DT_TEST_KEY)
assert_contains "--set 后 --get 能读取值" "_DT_TEST_KEY=hello123" "$out"

# 更新已有键
bash "$HELPER" --set _DT_TEST_KEY=world456 >/dev/null
out=$(bash "$HELPER" --get _DT_TEST_KEY)
assert_contains "--set 更新已有键" "_DT_TEST_KEY=world456" "$out"

# 多键查询
bash "$HELPER" --set _DT_TEST_KEY2=aaa >/dev/null
out=$(bash "$HELPER" --get _DT_TEST_KEY _DT_TEST_KEY2)
assert_contains "--get 多键返回第一个" "_DT_TEST_KEY=world456" "$out"
assert_contains "--get 多键返回第二个" "_DT_TEST_KEY2=aaa"     "$out"

# 查询不存在的键
out=$(bash "$HELPER" --get _DT_NONEXISTENT_KEY_XYZ)
assert_contains "--get 不存在键提示未设置" "未设置" "$out"

# --config 包含测试键
out=$(bash "$HELPER" --config)
assert_contains "--config 包含测试键" "_DT_TEST_KEY" "$out"

# --set 格式错误
assert_exit_nonzero "--set 无等号时报错" bash "$HELPER" --set INVALID_FORMAT

# 清理测试键
sed -i '/^_DT_TEST_KEY/d' ~/.dingtalk-skills/config

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "【3】未知命令报错"
# ─────────────────────────────────────────────────────────────────────────────

assert_exit_nonzero "未知命令 --foobar 报错" bash "$HELPER" --foobar

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "【4】新版 Token（--token / --token-info / --clear-token）"
# ─────────────────────────────────────────────────────────────────────────────

if [ -z "$DINGTALK_APP_KEY" ]; then
  sk "--token 相关测试" "DINGTALK_APP_KEY 未配置"
else
  # 清除缓存，强制重新获取
  bash "$HELPER" --clear-token >/dev/null

  out=$(bash "$HELPER" --token-info)
  assert_contains "--clear-token 后 token-info 显示无缓存" "无缓存" "$out"

  # 获取新 token
  token=$(bash "$HELPER" --token)
  if [ ${#token} -gt 20 ]; then
    ok "--token 返回有效 token（长度 ${#token}）"
  else
    ng "--token 返回 token 太短或为空" "长度>20" "${#token}"
  fi

  # 第二次应命中缓存
  token2=$(bash "$HELPER" --token)
  if [ "$token" = "$token2" ]; then
    ok "--token 第二次命中缓存，值相同"
  else
    ng "--token 第二次应命中缓存" "值相同" "值不同"
  fi

  # token-info 显示有效
  out=$(bash "$HELPER" --token-info)
  assert_contains "--token-info 显示有效" "有效" "$out"
  assert_contains "--token-info 显示剩余秒数" "剩余" "$out"

  # clear-token 后无缓存
  bash "$HELPER" --clear-token >/dev/null
  out=$(bash "$HELPER" --token-info)
  assert_contains "--clear-token 后 token-info 再次显示无缓存" "无缓存" "$out"
fi

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "【5】旧版 Token（--old-token）"
# ─────────────────────────────────────────────────────────────────────────────

if [ -z "$DINGTALK_APP_KEY" ]; then
  sk "--old-token 测试" "DINGTALK_APP_KEY 未配置"
else
  old_token=$(bash "$HELPER" --old-token)
  if [ ${#old_token} -gt 20 ]; then
    ok "--old-token 返回有效 token（长度 ${#old_token}）"
  else
    ng "--old-token 返回 token 太短或为空" "长度>20" "${#old_token}"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "【6】身份转换（--to-unionid / --to-userid）"
# ─────────────────────────────────────────────────────────────────────────────

if [ -z "$DINGTALK_MY_USER_ID" ]; then
  sk "userId→unionId 测试" "tests/.env 缺少 DINGTALK_MY_USER_ID"
else
  user_id="$DINGTALK_MY_USER_ID"

  # 清除临时 config 中的 OPERATOR_ID，测试自动写入
  sed -i '/^DINGTALK_MY_OPERATOR_ID=/d' "$TEMP_CONFIG"

  # 不传参：转换自身，应写入 DINGTALK_MY_OPERATOR_ID
  union_id=$(bash "$HELPER" --to-unionid 2>/dev/null)
  if [ ${#union_id} -gt 5 ]; then
    ok "--to-unionid 无参数返回 unionId（长度 ${#union_id}）"
  else
    ng "--to-unionid 无参数" "非空 unionId" "$union_id"
  fi

  saved=$(require_config DINGTALK_MY_OPERATOR_ID)
  if [ "$saved" = "$union_id" ]; then
    ok "--to-unionid 无参数自动写入 DINGTALK_MY_OPERATOR_ID"
  else
    ng "--to-unionid 自动写入配置" "$union_id" "$saved"
  fi

  # 传参：转换指定 userId，不应改变配置
  union_id2=$(bash "$HELPER" --to-unionid "$user_id" 2>/dev/null)
  if [ "$union_id2" = "$union_id" ]; then
    ok "--to-unionid 传参 userId 结果与无参数一致"
  else
    ng "--to-unionid 传参结果应与无参数一致" "$union_id" "$union_id2"
  fi

  # 传入他人 userId 时不覆盖 DINGTALK_MY_OPERATOR_ID
  saved2=$(require_config DINGTALK_MY_OPERATOR_ID)
  if [ "$saved2" = "$saved" ]; then
    ok "--to-unionid 传参不写入/覆盖 DINGTALK_MY_OPERATOR_ID"
  else
    ng "--to-unionid 传参不应修改配置" "$saved" "$saved2"
  fi

  # --to-userid：反向转换
  back_user_id=$(bash "$HELPER" --to-userid "$union_id" 2>/dev/null)
  if [ "$back_user_id" = "$user_id" ]; then
    ok "--to-userid 反向转换结果正确"
  else
    ng "--to-userid 反向转换" "$user_id" "$back_user_id"
  fi

  # --to-userid 无参数应报错
  assert_exit_nonzero "--to-userid 无参数报错" bash "$HELPER" --to-userid
fi

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "================================================================="
echo " 结果汇总：✅ $pass 通过   ❌ $fail 失败   ⏭️  $skip 跳过"
echo "================================================================="

[ "$fail" -eq 0 ]
