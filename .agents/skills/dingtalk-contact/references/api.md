# dingtalk-contact API 参考

> 所有接口均已验证可用。
> `NEW_TOKEN` = 新版 token（`api.dingtalk.com` 用），获取方式 `bash scripts/dt_helper.sh --token`
> `OLD_TOKEN` = 旧版 token（`oapi.dingtalk.com` 用），获取方式`bash scripts/dt_helper.sh --old-token`

---

## 1. 按关键词搜索用户

```
POST https://api.dingtalk.com/v1.0/contact/users/search
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "queryWord": "张三",
  "offset":    0,
  "size":      20
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `queryWord` | string | ✅ | 搜索关键词，不可为空 |
| `offset` | int | ❌ | 分页偏移量，默认 0 |
| `size` | int | ❌ | 每页数量，最大 20 |

响应：
```json
{
  "hasMore":    false,
  "totalCount": 1,
  "list":       ["25262904"]
}
```

> ⚠️ `list` 中存放的是 **userId**（字符串），不是 unionId。

---

## 2. 获取用户完整详情

```
POST https://oapi.dingtalk.com/topapi/v2/user/get?access_token={OLD_TOKEN}
```

请求体：
```json
{
  "userid":   "25262904",
  "language": "zh_CN"
}
```

响应（`result` 字段）：
```json
{
  "userid":       "25262904",
  "unionid":      "dGJ...",
  "name":         "张三",
  "title":        "高级工程师",
  "job_number":   "EMP001",
  "mobile":       "138xxxx0000",
  "state_code":   "86",
  "email":        "zhangsan@example.com",
  "org_email":    "zhangsan@corp.com",
  "dept_id_list": [932988755, 933257043],
  "dept_order_list":    [{"dept_id": 932988755, "order": 0}],
  "dept_position_list": [{"dept_id": 932988755, "title": "工程师"}],
  "role_list":          [{"id": 123, "name": "管理员", "group_name": "组织架构"}],
  "hired_date": 1640000000000,
  "active":     true,
  "admin":      false,
  "boss":       false
}
```

> ⚠️ 返回体中 `result.unionid`（无下划线）有值，`result.union_id`（有下划线）可能为空。

errcode 说明：0=成功；60121=用户不存在；40014=token 无效。

---

## 3. unionId → userId 转换

```
POST https://oapi.dingtalk.com/topapi/user/getbyunionid?access_token={OLD_TOKEN}
```

请求体：
```json
{
  "unionid": "dGJ..."
}
```

响应：
```json
{
  "errcode": 0,
  "errmsg":  "ok",
  "result": {
    "contact_type": 0,
    "userid":       "25262904"
  }
}
```

> `contact_type=0` 企业内部员工；`contact_type=1` 外部联系人。

---

## 4. 企业员工总人数

```
POST https://oapi.dingtalk.com/topapi/user/count?access_token={OLD_TOKEN}
```

请求体：
```json
{ "only_active": false }
```

`only_active=true` 仅统计激活员工；`false` 统计全部。

响应：
```json
{
  "errcode": 0,
  "errmsg":  "ok",
  "result":  { "count": 2192 }
}
```

---

## 5. 按关键词搜索部门

```
POST https://api.dingtalk.com/v1.0/contact/departments/search
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "queryWord": "技术",
  "offset":    0,
  "size":      20
}
```

响应：
```json
{
  "hasMore":    false,
  "totalCount": 2,
  "list":       [932988755, 933257043]
}
```

> `list` 返回部门 ID（整数）。根部门 ID = `1`。

---

## 6. 获取子部门列表

```
POST https://oapi.dingtalk.com/topapi/v2/department/listsub?access_token={OLD_TOKEN}
```

请求体：
```json
{ "dept_id": 1, "language": "zh_CN" }
```

响应（`result` 为数组）：
```json
[
  {
    "dept_id":   932988755,
    "name":      "技术部",
    "parent_id": 1,
    "auto_add_user": false,
    "dept_manager_userid_list": ["25262904"]
  }
]
```

---

## 7. 获取子部门 ID 列表

```
POST https://oapi.dingtalk.com/topapi/v2/department/listsubid?access_token={OLD_TOKEN}
```

请求体：
```json
{ "dept_id": 1 }
```

响应：
```json
{
  "errcode": 0,
  "result":  { "dept_id_list": [932988755, 933257043, 933035510] }
}
```

> 仅返回直接子部门，不递归多层。如需完整树，循环调用此接口。

---

## 8. 获取部门详情

```
POST https://oapi.dingtalk.com/topapi/v2/department/get?access_token={OLD_TOKEN}
```

请求体：
```json
{ "dept_id": 932988755, "language": "zh_CN" }
```

响应（`result`）：
```json
{
  "dept_id":      932988755,
  "name":         "技术部",
  "parent_id":    1,
  "member_count": 32,
  "order":        100,
  "auto_add_user": false,
  "hide_dept":    false
}
```

---

## 9. 获取部门成员完整列表

```
POST https://oapi.dingtalk.com/topapi/v2/user/list?access_token={OLD_TOKEN}
```

请求体：
```json
{
  "dept_id":              932988755,
  "cursor":               0,
  "size":                 100,
  "order_field":          "custom",
  "contain_access_level": false,
  "language":             "zh_CN"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `dept_id` | int | ✅ | 部门 ID |
| `cursor` | int | ✅ | 分页游标，首次传 0 |
| `size` | int | ✅ | 每页数量，最大 100 |
| `order_field` | string | ❌ | `custom`=自定义排序 |

响应（`result`）：
```json
{
  "has_more":    true,
  "next_cursor": 100,
  "list": [
    {
      "userid":       "25262904",
      "unionid":      "dGJ...",
      "name":         "张三",
      "title":        "工程师",
      "job_number":   "EMP001",
      "mobile":       "138xxxx0000",
      "dept_id_list": [932988755],
      "active":       true
    }
  ]
}
```

> 分页：`has_more=true` 时，用 `next_cursor` 作为下次请求的 `cursor`。

---

## 10. 获取部门成员 userId 列表

```
POST https://oapi.dingtalk.com/topapi/user/listid?access_token={OLD_TOKEN}
```

请求体：
```json
{ "dept_id": 932988755 }
```

响应：
```json
{
  "errcode": 0,
  "result":  { "userid_list": ["25262904", "12345678"] }
}
```

---

## 11. 获取用户所在部门路径

```
POST https://oapi.dingtalk.com/topapi/v2/department/listparentbyuser?access_token={OLD_TOKEN}
```

请求体：
```json
{ "userid": "25262904" }
```

响应：
```json
{
  "errcode": 0,
  "result": {
    "parent_list": [
      { "parent_dept_id_list": [932988755, 933257043, 1] }
    ]
  }
}
```

> `parent_dept_id_list` 从直属部门到根部门（`1`）排列。
> 用户可能同时属于多个部门，`parent_list` 每项对应一条路径。

---

## 错误码

| errcode | 含义 | 处理建议 |
|---|---|---|
| 0 | 成功 | — |
| 40014 | token 无效或过期 | 删除缓存，重新获取 token |
| 60003 | 部门 ID 不存在 | 检查 dept_id 是否正确 |
| 60121 | 用户不存在 | 检查 userId 是否正确 |
| 60122 | unionId 不存在 | 检查 unionId 是否正确 |
| 88 | 没有操作权限 | 在钉钉开放平台申请对应接口权限 |
| 400 | 参数错误 | 检查 queryWord 不为空等参数约束 |

---

## 所需应用权限

| 权限 | 用途 |
|---|---|
| `qyapi_addresslist_search` | 按关键词搜索用户/部门 |
| `Contact.User.Read` | 读取用户详情（企业内部应用通常默认有） |
