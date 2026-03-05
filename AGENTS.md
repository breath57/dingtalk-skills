# AGENTS.md

本文件为 AI Agent 提供操作本仓库所需的背景信息与行为规范。

---

## 项目简介

**dingtalk-skills** 是一个面向 AI Agent 的钉钉开放平台技能库，遵循 [anthropics/skills](https://github.com/anthropics/skills) 规范，每个技能以 `SKILL.md` 定义，可通过 `npx skills add` 安装到 Agent 项目中。

---

## 仓库结构

```
dingtalk-skills/
├── AGENTS.md                          # 本文件，给 Agent 看的项目说明
├── README.md                          # 中文文档
├── README_EN.md                       # English documentation
├── skills-lock.json                   # 技能依赖锁定文件（勿手动修改）
└── .agents/
    └── skills/
        ├── skill-creator/             # 技能开发工具（由 anthropics 提供）
        ├── dingtalk-document/         # 钉钉知识库与文档技能
        │   ├── SKILL.md
        │   └── references/
        │       └── api.md
        └── dingtalk-ai-table/         # 钉钉 AI 表格技能
            ├── SKILL.md
            └── references/
                └── api.md
```

---

## 技能目录

| 技能名称 | 路径 | 状态 | 功能描述 |
|---|---|---|---|
| `dingtalk-document` | `.agents/skills/dingtalk-document/` | ✅ 可用 | 钉钉知识库与文档的创建、查询、目录浏览、成员管理 |
| `dingtalk-ai-table` | `.agents/skills/dingtalk-ai-table/` | ✅ 可用 | 钉钉 AI 表格的工作表管理、单元格读写、行列操作 |
| `skill-creator` | `.agents/skills/skill-creator/` | ✅ 可用 | 技能开发框架（由 anthropics/skills 提供） |

---

## 开发新技能的规范

在本仓库中新增钉钉技能时，需遵循以下约定：

### 1. 文件结构
```
.agents/skills/<skill-name>/
├── SKILL.md              # 必须：技能主文件
└── references/
    └── api.md            # 推荐：API 参考（避免 SKILL.md 过长）
```

### 2. SKILL.md 格式

```yaml
---
name: <技能名称，使用英文小写连字符>
description: <触发描述，必须包含中文关键词，覆盖用户可能说的各种表达>
---
```

- `description` 是 Agent 用来判断是否加载该技能的关键字段，**务必包含完整的场景关键词**
- 正文使用**全中文**撰写，技术术语（HTTP 方法、JSON 字段、API 路径）保持英文

### 3. 语言规范
- 所有 `SKILL.md` 和 `references/api.md`：**全中文**（技术术语除外）
- `README.md`：中文
- `README_EN.md`：English
- `AGENTS.md`（本文件）：中文

### 4. API 文档规范
- `references/api.md` 中保留完整的请求/响应 JSON 示例
- 错误码表需包含：错误码、说明、建议处理方式
- 所有接口须注明所需的钉钉应用权限

---

## 提交规范

采用约定式提交（Conventional Commits）：

| 类型 | 适用场景 |
|---|---|
| `feat(<skill>):` | 新增技能或技能新功能 |
| `fix(<skill>):` | 修复技能逻辑或 API 错误 |
| `docs:` | 更新文档（README、AGENTS.md 等） |
| `chore:` | 维护性变更（依赖更新、配置修改等） |
| `refactor(<skill>):` | 重构技能结构，无功能变化 |

示例：
```
feat(dingtalk-document): 新增文档内容读写支持
fix(dingtalk-ai-table): 修正区域地址格式校验逻辑
docs: 更新 README 添加安装说明
```

---

## 注意事项

- **不要**在代码或文档中硬编码 `appKey`、`appSecret`、`accessToken` 等凭证
- `skills-lock.json` 由 `npx skills` 自动维护，**不要手动修改**
- 新增技能后，同步更新 `README.md` 和 `README_EN.md` 的技能列表
- PR 合并前确保 `SKILL.md` 的 `description` 已覆盖常见触发场景

---

## 相关链接

- [钉钉开放平台文档](https://open.dingtalk.com/document/)
- [anthropics/skills 规范](https://github.com/anthropics/skills)
- [本仓库 GitHub](https://github.com/breath57/dingtalk-skills)
