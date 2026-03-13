#!/bin/bash
# =============================================================================
# common_scripts_load.sh — 将 scripts/common/ 下的公共脚本分发到各 skill
# 用法: bash scripts/common_scripts_load.sh [--force] [--dry-run]
#   --force    已存在的文件也更新（默认跳过）
#   --dry-run  预览操作，不实际写入
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# 配置：要分发的目标 skill 列表
# 注释掉某行即可跳过该 skill
# ─────────────────────────────────────────────────────────────────────────────
TARGET_SKILLS=(
#   dingtalk-ai-table
#   dingtalk-document
#   dingtalk-message
#   dingtalk-skill-creator
#   dingtalk-todo
  dingtalk-contact
)

# 配置：要分发的文件列表（相对于 scripts/common/）
COMMON_FILES=(
  dt_helper.sh
)

# ─────────────────────────────────────────────────────────────────────────────
# 以下无需修改
# ─────────────────────────────────────────────────────────────────────────────
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMON_DIR="$REPO_ROOT/scripts/common"
SKILLS_DIR="$REPO_ROOT/.agents/skills"
DRY_RUN=false
FORCE=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --force)   FORCE=true ;;
  esac
done

if "$DRY_RUN"; then echo "（dry-run 模式，不实际写入）"; fi
if "$FORCE";   then echo "（--force：已存在的文件也将被更新）"; fi

echo "公共脚本目录: $COMMON_DIR"
echo "目标 skill 根目录: $SKILLS_DIR"
echo "─────────────────────────────────"

total_copied=0
total_skipped=0

for skill in "${TARGET_SKILLS[@]}"; do
  skill_dir="$SKILLS_DIR/$skill"
  if [ ! -d "$skill_dir" ]; then
    echo "⚠️  $skill — 目录不存在，跳过"
    continue
  fi

  dest_dir="$skill_dir/scripts"
  skill_copied=0
  skill_skipped=0

  for file in "${COMMON_FILES[@]}"; do
    src="$COMMON_DIR/$file"
    dest="$dest_dir/$file"

    if [ ! -f "$src" ]; then
      echo "⚠️  $skill/$file — 源文件不存在: $src"
      continue
    fi

    if [ -f "$dest" ] && ! "$FORCE"; then
      echo "⏭️  $skill/$file — 已存在，跳过（加 --force 可更新）"
      skill_skipped=$((skill_skipped + 1))
      total_skipped=$((total_skipped + 1))
      continue
    fi

    if "$DRY_RUN"; then
      echo "[dry-run] $skill/$file"
    else
      mkdir -p "$dest_dir"
      cp "$src" "$dest"
      chmod +x "$dest"
      echo "✅ $skill/$file"
    fi
    skill_copied=$((skill_copied + 1))
    total_copied=$((total_copied + 1))
  done
done

echo "─────────────────────────────────"
if "$DRY_RUN"; then
  echo "共 $total_copied 个文件将写入，$total_skipped 个将跳过（dry-run，未执行）"
else
  echo "共写入 $total_copied 个文件，跳过 $total_skipped 个"
fi
