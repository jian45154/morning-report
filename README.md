# Morning Report

每天早上自动生成正在推进项目的中文早报，并以中文语音发送到 Discord。后续也可以扩展到 Slack、企业微信、飞书或其他平台。

## 当前范围

- 从 JSON 配置读取 `active` 项目。
- 生成中文文本早报。
- 可选生成中文语音 MP3。
- 通过 Discord webhook 发送文本和语音文件。
- 通过 GitHub Actions 每天定时运行，也支持手动触发。

## 快速开始

```powershell
python -m pip install -e ".[tts]"
copy config\projects.example.json config\projects.json
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python -m morning_report --projects config\projects.json --tts-provider edge --send-discord
```

不需要语音时：

```powershell
python -m morning_report --projects config\projects.json --tts-provider none
```

## GitHub Actions 配置

在仓库的 Settings -> Secrets and variables -> Actions 中添加：

- `DISCORD_WEBHOOK_URL`: Discord webhook 地址。

默认 workflow 使用 `zh-CN-XiaoxiaoNeural` 生成中文语音。固定 cron 无法自动处理澳洲夏令时；如果需要严格本地早上 8 点，需要按季节调整 `.github/workflows/morning-report.yml` 的 UTC 时间。

## 项目配置

复制 `config/projects.example.json` 到 `config/projects.json`，只保留正在推进或需要汇报的项目。

字段约定：

- `name`: 项目名称。
- `status`: `active` 才会进入早报。
- `goal`: 当前目标。
- `progress`: 已推进的内容。
- `next`: 今天或下一步要推进的内容。
- `blockers`: 风险或阻塞，可以为空数组。

