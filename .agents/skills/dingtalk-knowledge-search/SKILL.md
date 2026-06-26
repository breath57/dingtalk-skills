---
name: dingtalk-knowledge-search
description: 钉钉知识库搜索与读取。用于在钉钉沉淀知识里快速查资料、理解项目背景、梳理团队/部门信息、回答制度问题、整理新人入门材料、读取文档正文、导出 Markdown、下载文件，并可带图片和 diagram。
---

## 用法

```bash
cd <the_skill_dir_path>/scripts
python3 cli.py config check
python3 cli.py search "关键词1 关键词2 关键词3"
python3 cli.py read "https://alidocs.dingtalk.com/i/nodes/<node_id>"
python3 cli.py read <node_id>
```

## 配置

先运行配置校验：

```bash
python3 cli.py config check
```

需要这些配置：

| 配置 | 用途 | 获取方式 |
| --- | --- | --- |
| `DINGTALK_APP_KEY` | 调用钉钉开放平台 API | 钉钉开放平台 -> 应用管理 -> 企业内部应用 -> 凭证与基础信息 |
| `DINGTALK_APP_SECRET` | 获取 API token | 同上，应用凭证信息中查看 |
| `DINGTALK_MY_USER_ID` | 当前操作者身份 | 管理后台 -> 通讯录 -> 成员管理 -> 点击成员查看 userId |
| `DINGTALK_MY_OPERATOR_ID` | 文档 API 的 operatorId/unionId | 有 `DINGTALK_MY_USER_ID` 后可自动转换 |

缺少 `DINGTALK_MY_OPERATOR_ID` 时执行：

```bash
python3 cli.py config to-unionid
```

## 得到什么

- `search`：返回匹配文档列表；可用 `--limit <n>` 控制数量
- `read`：返回 Markdown；长内容会写到文件并返回路径；非 ALIDOC 文件会下载原文件
- PDF 转文本：`read <pdf_node_or_url> --mode pdf2text` 会先下载 PDF，再用系统 `pdftotext -layout` 输出 `.txt`；如果系统没有 `pdftotext`，会提示安装 `poppler-utils`，并退回返回 PDF 路径
- 默认输出：写到 skill workspace 下的 `.skills-workspace/dingtalk-knowledge-search/outputs/`
- 项目沉淀：用 `--output-dir "$PWD/dingtalk-docs" --output-path` 把结果写到当前项目
- 输出缓存：下载/转换结果会在用户级缓存目录保留一份，远端 `modifiedTime` 未变化时复用；默认用硬链接写入 `--output-dir`，用 `--output-strategy copy` 可复制隔离
- 图片本地化：用 `--with img-local`，图片会下载到 Markdown 同目录 `.assets/<文档名>/`
- 图片代理：用 `--with img`，节约本地空间，但依赖代理服务和原链接有效期
- diagram：用 `--with diagram` 一起导出

## 例子

```bash
python3 cli.py search "项目背景 年假 晋升" --limit 10
python3 cli.py read "https://alidocs.dingtalk.com/i/nodes/<node_id>" --output-dir "$PWD/dingtalk-docs" --output-path
python3 cli.py read "https://alidocs.dingtalk.com/i/nodes/<node_id>" --with img-local --with diagram --output-dir "$PWD/dingtalk-docs" --output-path
python3 cli.py read "https://alidocs.dingtalk.com/i/nodes/<file_node_id>" --output-dir "$PWD/dingtalk-docs"
python3 cli.py read "https://alidocs.dingtalk.com/i/nodes/<pdf_node_id>" --mode pdf2text --output-dir "$PWD/dingtalk-docs"
python3 cli.py read "https://alidocs.dingtalk.com/i/nodes/<pdf_node_id>" --mode pdf2text --output-dir "$PWD/dingtalk-docs" --output-strategy copy
```

## 缓存

- `search` 不缓存，每次直接查远端
- `node`、`resolve-url`、`blocks` 仍使用 SQLite API 缓存，受 `--cache-ttl` 影响
- 输出文件缓存不受 TTL 影响，使用远端 `modifiedTime` 判断是否复用
- 输出缓存默认位置：`~/.dingtalk-skills/dingtalk-knowledge-search/output-cache/`
- 默认 `--output-strategy link`：把全局缓存硬链接到当前 `--output-dir`，节省空间；编辑任一硬链接文件会影响同一份内容
- `--output-strategy copy`：复制到当前 `--output-dir`，和全局缓存隔离
- `python3 cli.py cache clear --namespace output --yes` 会删除输出缓存记录和关联本地文件

## 登录

- 需要扫码时，命令会返回 `loginRequired: true` 和 `screenshotPath`
- 扫码后重新执行同一个命令
