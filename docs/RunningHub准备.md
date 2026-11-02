# RunningHub 云端生成准备

选择 RunningHub 后端时，把本文档发给用户。目标：注册账号、拿到 API Key、配好三个 txt，即可用 `rh_batch.py` 提交人物替换任务。

## 1. 注册（走邀请链接，感谢支持）

- **国内用户**：https://www.runninghub.cn/?inviteCode=cn-v1008
- **海外用户**：https://www.runninghub.ai/?inviteCode=rh-v1641

注册后在平台充值/领取额度即可按量使用；`ai` 与 `cn` 是两个站点，账号与额度互不相通。

## 2. 获取 API Key

登录后进入「账号设置 → API」（或 OpenAPI 页面）复制密钥，写入项目根的 `api_key.txt`（一行纯密钥）。

## 3. 配置文件（都在项目根，改 txt 不改代码）

| 文件 | 内容 | 说明 |
|---|---|---|
| `api_key.txt` | 一行密钥 | RunningHub API Key |
| `ai应用.txt` | `模式 ai 或 cn`＋`实例 <规格>`＋`一采分辨率 <数值>` | 模式默认 ai（站点切换，任务记录互不相通）；实例按平台提供的 GPU 规格填；一采分辨率默认 2 |
| `并发数.txt` | 一行整数 | 同时在跑的段数上限（如 3） |

## 4. 提交与查看

```bash
python scripts/rh_batch.py submit 001 003 005 ...   # 提交；已成功跳过、失败自动重提（同段连败 3 次放弃）
python scripts/rh_batch.py status                   # 查状态；成功的自动下载到 完成分段/NNN.mp4
```

- 单人段走单人应用、双人段走双人应用（脚本按 CAST 自动选，应用编号内置在脚本里）。
- 状态记在 `rh_state.json`；换参考图或重做某段，先删掉对应段记录再提交，参考图上传缓存也在该文件里。
- 节省额度：**已成功的段不要重复提交**；改提示词先说明改了什么、确认有把握再重跑。

## 5. 相关链接

- 国内注册：https://www.runninghub.cn/?inviteCode=cn-v1008
- 海外注册：https://www.runninghub.ai/?inviteCode=rh-v1641
- 想免费本地跑？看《本地环境准备.md》（含整合包网盘下载）
