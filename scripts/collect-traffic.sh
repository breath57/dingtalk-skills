#!/usr/bin/env bash
# collect-traffic.sh — 每日拉取 GitHub Traffic 数据并更新看板
# 用法:
#   ./scripts/collect-traffic.sh              # 采集 + 合并
#   ./scripts/collect-traffic.sh --commit     # 采集 + 合并 + git commit + push
#
# 建议 crontab (每天 09:00 执行，自动提交):
#   0 9 * * * /path/to/scripts/collect-traffic.sh --commit >> /path/to/docs/traffic/traffic.log 2>&1

set -euo pipefail

REPO="breath57/dingtalk-skills"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TRAFFIC_DIR="$ROOT_DIR/traffic"
RAW_DIR="$TRAFFIC_DIR/raw"
DATE="$(date -u +%Y-%m-%d)"

mkdir -p "$RAW_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# 检查 gh 认证
if ! gh auth status &>/dev/null; then
  log "ERROR: gh CLI 未认证，请先运行: gh auth login"
  exit 1
fi

log "开始采集 $REPO 的 traffic 数据 ($DATE) ..."

gh api "repos/$REPO/traffic/clones" \
  > "$RAW_DIR/clones-$DATE.json" && log "✓ clones 已保存"

gh api "repos/$REPO/traffic/views" \
  > "$RAW_DIR/views-$DATE.json" && log "✓ views 已保存"

gh api "repos/$REPO" --jq '{stars: .stargazers_count, forks: .forks_count}' \
  > "$RAW_DIR/repo-$DATE.json" && log "✓ repo stats 已保存"

log "合并数据到 data.js ..."
python3 "$SCRIPT_DIR/merge_traffic.py"

log "✅ 完成。查看看板:"
log "   cd traffic && python3 -m http.server 8080"
log "   然后打开 http://localhost:8080"

# --commit 模式：自动提交并推送
if [[ "${1:-}" == "--commit" ]]; then
  cd "$ROOT_DIR"
  git add traffic/data.js "traffic/raw/clones-$DATE.json" \
          "traffic/raw/views-$DATE.json" "traffic/raw/repo-$DATE.json" 2>/dev/null || true
  if git diff --cached --quiet; then
    log "无变动，跳过提交。"
  else
    git commit -m "chore(traffic): 每日数据更新 [$DATE]"
    git push origin main
    log "✓ 已提交并推送"
  fi
fi
