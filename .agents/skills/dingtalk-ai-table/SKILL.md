---
name: dingtalk-ai-table
description: 钉钉 AI 表格（电子表格）操作。当用户提到"钉钉表格"、"AI表格"、"工作表"、"单元格"、"读取表格"、"写入表格"、"插入行"、"删除列"、"更新数据"、"dingtalk spreadsheet"、"dingtalk table"时使用此技能。支持读写单元格区域、管理工作表、插入/删除行列等全部表格操作。
---

# 钉钉 AI 表格技能

负责钉钉 AI 表格（电子表格）的所有操作，通过钉钉开放平台 API 实现。

一个**工作簿**（`workbookId`）包含一个或多个**工作表**（`sheetId`），数据通过**单元格区域**（如 `A1:C10`）寻址。

API 详情见 `references/api.md`。

---

## 认证

```
POST https://api.dingtalk.com/v1.0/oauth2/accessToken
Content-Type: application/json

{ "appKey": "<应用 appKey>", "appSecret": "<应用 appSecret>" }
```

所有请求需携带：`x-acs-dingtalk-access-token: <accessToken>`

若用户未提供 `appKey`、`appSecret`、`workbookId`，主动询问。

---

## 如何获取 workbookId

`workbookId` 存在于表格的分享链接中：
```
https://alidocs.dingtalk.com/i/nodes/<workbookId>?...
```

请用户提供表格链接，从中提取节点 ID 片段。

---

## 核心操作

### 1. 列出工作簿中所有工作表

操作前先了解有哪些工作表：

```
GET https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets
x-acs-dingtalk-access-token: <accessToken>
```

返回 `[{ sheetId, name, index }]` 数组。

---

### 2. 查询单个工作表

```
GET https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}
```

---

### 3. 新建工作表

```
POST https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets
Content-Type: application/json

{
  "name": "<工作表名称>",
  "index": 0
}
```

`index` 为 0 开始的插入位置（可省略，默认追加到末尾）。

---

### 4. 删除工作表

```
DELETE https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}
```

⚠️ 不可恢复，执行前需用户确认。

---

### 5. 读取单元格区域（最常用操作）

```
GET https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}/ranges/{区域地址}
```

区域地址格式：`A1:C10`（第 A 到 C 列，第 1 到 10 行）

读取全部数据时建议使用 `A1:Z1000`，或先询问用户实际数据范围。

返回 `values`：二维数组，每个子数组对应一行。

示例（`A1:C3`）：
```json
{
  "values": [
    ["姓名", "分数", "日期"],
    ["张三", 95, "2026-01-01"],
    ["李四", 87, "2026-01-02"]
  ]
}
```

---

### 6. 写入单元格区域

```
PUT https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}/ranges/{区域地址}
Content-Type: application/json

{
  "values": [
    ["列头1", "列头2", "列头3"],
    ["第1行1列", "第1行2列", "第1行3列"]
  ]
}
```

`values` 的行列数必须与区域地址维度一致。
写入公式时以 `=` 开头，如 `"=SUM(A1:A10)"`。

---

### 7. 插入行

```
POST https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}/insertRows
Content-Type: application/json

{
  "row": 2,
  "rowCount": 3
}
```

在第 `row` 行（0 开始）**上方**插入 `rowCount` 行空白行。

---

### 8. 插入列

```
POST https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}/insertColumns
Content-Type: application/json

{
  "column": 1,
  "columnCount": 2
}
```

在第 `column` 列（0 开始）**左侧**插入 `columnCount` 列。

---

### 9. 删除行

```
DELETE https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}/rows/{row}
Content-Type: application/json

{ "rowCount": 2 }
```

从 `row`（0 开始）起删除 `rowCount` 行。⚠️ 执行前确认。

---

### 10. 删除列

```
DELETE https://api.dingtalk.com/v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}/columns/{column}
Content-Type: application/json

{ "columnCount": 1 }
```

---

### 11. 清除区域数据

仅清除数据（保留格式）：
```
DELETE .../ranges/{区域地址}/values
```

清除全部内容（含格式）：
```
DELETE .../ranges/{区域地址}/contents
```

---

### 12. 隐藏 / 显示行列

**隐藏行：**
```
PUT .../rows/{row}/visibility
{ "hidden": true, "count": 3 }
```

**显示行：**
```
PUT .../rows/{row}/visibility
{ "hidden": false, "count": 3 }
```

列操作路径相同，将 `rows` 替换为 `columns`。

---

## 典型场景

### "读取钉钉表格 Sheet1 的数据"
1. 询问 workbookId（从链接获取）和工作表名称
2. `GET /sheets` 找到对应 sheetId
3. `GET /sheets/{sheetId}/ranges/A1:Z500` 读取内容
4. 整理成表格或摘要形式展示

### "往表格里写入一批数据"
1. 确认目标工作表和起始单元格（如 `A2`）
2. 根据数据维度确定结束单元格
3. `PUT /sheets/{sheetId}/ranges/A2:D10`，传入 `values` 数组
4. 告知用户写入成功

### "在第 3 行前插入 2 行空白行"
1. `POST /insertRows`，传入 `{ "row": 2, "rowCount": 2 }`
2. 告知操作结果

### "新建一个叫'汇总'的工作表"
1. `POST /workbooks/{workbookId}/sheets`，传入 `{ "name": "汇总" }`
2. 返回新工作表的 sheetId

---

## 区域地址说明

| 格式 | 含义 |
|---|---|
| `A1` | 单个单元格 |
| `A1:C10` | A1 到 C10 的矩形区域 |
| `A:A` | 整列 A |
| `1:1` | 整行 1 |

---

## 错误处理

| HTTP 状态码 | 含义 | 处理方式 |
|---|---|---|
| 401 | token 过期 | 重新获取 accessToken |
| 403 | 权限不足 | 检查应用是否开通表格读写权限 |
| 404 | 工作簿或工作表不存在 | 确认 workbookId 和 sheetId |
| 400 | 区域地址格式错误 | 检查格式（如 `A1:C10`） |
| 429 | 触发限流 | 等待 1 秒后重试 |
