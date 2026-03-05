# 钉钉 AI 表格 API 参考

基础地址：`https://api.dingtalk.com/v1.0`

认证请求头：`x-acs-dingtalk-access-token: <accessToken>`

---

## 工作表（Sheet）

### 查询所有工作表
```
GET /doc/workbooks/{workbookId}/sheets
```

返回示例：
```json
{
  "sheets": [
    { "sheetId": "sheet1", "name": "Sheet1", "index": 0 },
    { "sheetId": "sheet2", "name": "汇总", "index": 1 }
  ]
}
```

---

### 查询单个工作表
```
GET /doc/workbooks/{workbookId}/sheets/{sheetId}
```

返回示例：
```json
{
  "sheetId": "sheet1",
  "name": "Sheet1",
  "index": 0,
  "rowCount": 1000,
  "columnCount": 26
}
```

---

### 创建工作表
```
POST /doc/workbooks/{workbookId}/sheets
请求体：
{
  "name": string（必填），
  "index": int（可选，0 开始，默认追加末尾）
}
```

返回：`{ "sheetId": "xxx", "name": "新工作表", "index": 2 }`

---

### 删除工作表
```
DELETE /doc/workbooks/{workbookId}/sheets/{sheetId}
```

返回：`204 No Content`

---

## 行列操作

### 插入行（在指定行上方）
```
POST /doc/workbooks/{workbookId}/sheets/{sheetId}/insertRows
请求体：
{
  "row": int,       // 0 开始，在此行上方插入
  "rowCount": int   // 插入行数
}
```

---

### 删除行
```
DELETE /doc/workbooks/{workbookId}/sheets/{sheetId}/rows/{row}
请求体：
{
  "rowCount": int   // 从 row 起删除的行数
}
```

---

### 设置行显示/隐藏
```
PUT /doc/workbooks/{workbookId}/sheets/{sheetId}/rows/{row}/visibility
请求体：
{
  "hidden": bool,
  "count": int（默认 1）
}
```

---

### 插入列（在指定列左侧）
```
POST /doc/workbooks/{workbookId}/sheets/{sheetId}/insertColumns
请求体：
{
  "column": int,      // 0 开始，在此列左侧插入
  "columnCount": int
}
```

---

### 删除列
```
DELETE /doc/workbooks/{workbookId}/sheets/{sheetId}/columns/{column}
请求体：
{
  "columnCount": int
}
```

---

### 设置列显示/隐藏
```
PUT /doc/workbooks/{workbookId}/sheets/{sheetId}/columns/{column}/visibility
请求体：
{
  "hidden": bool,
  "count": int（默认 1）
}
```

---

## 单元格区域（Range）

区域地址格式：标准 A1 表示法，如 `A1:C10`

### 读取区域值
```
GET /doc/workbooks/{workbookId}/sheets/{sheetId}/ranges/{区域地址}
```

返回示例：
```json
{
  "rangeAddress": "A1:C3",
  "values": [
    ["姓名", "分数", "日期"],
    ["张三", 95, "2026-01-01"],
    ["李四", 87, "2026-01-02"]
  ],
  "formulas": [
    ["", "", ""],
    ["", "=SUM(B2:B10)", ""]
  ]
}
```

`values`：单元格显示值（公式已计算）
`formulas`：原始公式字符串（无公式时为空字符串）

---

### 写入区域值
```
PUT /doc/workbooks/{workbookId}/sheets/{sheetId}/ranges/{区域地址}
请求体：
{
  "values": [
    ["值1", "值2", "值3"],
    ["值4", "值5", "值6"]
  ]
}
```

`values` 的行列数必须与区域地址维度一致。
写入公式以 `=` 开头，如 `"=SUM(A1:A10)"`。

---

### 清除区域数据（保留格式）
```
DELETE /doc/workbooks/{workbookId}/sheets/{sheetId}/ranges/{区域地址}/values
```

---

### 清除区域全部内容（含格式）
```
DELETE /doc/workbooks/{workbookId}/sheets/{sheetId}/ranges/{区域地址}/contents
```

---

## 列索引参考

| 列索引（0 开始）| 列字母 |
|---|---|
| 0 | A |
| 1 | B |
| 25 | Z |
| 26 | AA |

---

## 常见错误码

| 错误码 | 说明 |
|---|---|
| `InvalidParameter.RangeAddress` | 区域地址格式不正确 |
| `InvalidParameter.Values` | values 数组维度与区域不匹配 |
| `NotFound.Workbook` | workbookId 不存在 |
| `NotFound.Sheet` | sheetId 不存在 |
| `Forbidden.AccessDenied` | 应用缺少权限或未授权 |
| `LimitExceeded.Qps` | 触发限流，1 秒后重试 |

---

## 所需应用权限

在钉钉开放平台 → 应用 → 权限管理中开通：
- 读取表格内容
- 写入表格内容
- 管理表格
