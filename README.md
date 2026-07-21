# 香港電台《古今風雲人物》自托管 RSS

非官方 Podcast RSS：从 [节目重温](https://www.rthk.hk/radio/radio1/programme/People) 的公开接口拉取集数元数据，生成标准 RSS 2.0（含 iTunes 标签）。**音频仍由港台 CDN 提供**，本仓库不下载、不转码、不镜像音频。

官方 Podcast feed（`people.xml`）自约 2025-10 起因政策停更；本脚本用于个人订阅，请遵守港台条款与版权。

## 本地生成（P0）

需要 **Python 3.10+**（仅标准库，无第三方依赖）。

```bash
python generate_feed.py --out feed.xml
```

常用参数：

```bash
# 只保留最新 30 集
python generate_feed.py --out feed.xml --max-items 30

# 跳过对音频的 HEAD（更快；enclosure length=0）
python generate_feed.py --out feed.xml --skip-head

# 写入 atom:link rel=self（公网订阅 URL）
python generate_feed.py --out feed.xml --self-url https://YOUR_USER.github.io/rthk_rss/feed.xml
```

本地用播客客户端验证：

```bash
python -m http.server 8080
# 订阅 http://127.0.0.1:8080/feed.xml
```

## GitHub Pages 订阅（P1）

1. 将本仓库推送到 GitHub（建议公开仓，便于 Pages 与 Actions）。
2. 仓库 **Settings → Pages**：Source 选 **Deploy from a branch**，Branch 选 `main`（或 `master`）、`/ (root)`。
3. **Settings → Actions → General**：允许 workflow，并对 GITHUB_TOKEN 开启 **Read and write**（用于提交更新后的 `feed.xml`）。
4. 打开 **Actions** 标签，手动运行 **Generate RSS feed**，或等待定时任务。
5. 订阅地址（将 `YOUR_USER` / 仓库名换成你的）：

   ```
   https://YOUR_USER.github.io/rthk_rss/feed.xml
   ```

定时：每天 UTC 01:00，以及周六 UTC 13:00（约 HKT 21:00，贴近周六 20:00 播出后）。生成失败时不会用空 feed 覆盖（脚本非零退出且不写文件）。

**隐私说明：** 本项目**不需要、也不使用**任何 API 密钥或 GitHub Secrets。公开仓会暴露 GitHub 用户名（出现在 Pages URL）。音频直链港台 CDN，不经过本仓库。

## 验收要点

- 最新 `<item>` 日期应与官网重温一致（应明显新于官方 RSS 停更的 2025-09）。
- enclosure 形如：  
  `https://archive.rthk.hk/mp3/radio/archive/radio1/People/m4a/YYYYMMDD.m4a`  
  用浏览器或 `curl -I` 应返回 `200`、`Content-Type: audio/mp4`。
- `guid` 稳定：`rthk-people-{集数id}`。

## 目录

| 文件 | 说明 |
|------|------|
| `generate_feed.py` | 拉取 catchUp、生成 `feed.xml` |
| `feed.xml` | 生成物（Actions 会更新并提交） |
| `.github/workflows/generate-feed.yml` | 定时 / 手动生成 |
| `rthk-people-rss-plan.md` | 接口调研与方案交接 |

## 免责

非官方、非港台产品。仅供个人学习与订阅便利；请勿将音频二次上传至公共镜像站做商业分发。
