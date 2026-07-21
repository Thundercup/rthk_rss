# 港台《古今風雲人物》自托管 RSS 方案

> 交接文档：供其他 Agent 直接实现。  
> 编写日期：2026-07-21  
> 状态：方案已验证接口，待实现

---

## 1. 背景与问题

### 节目信息

| 项 | 值 |
|----|-----|
| 节目名 | 古今風雲人物 |
| 频道 | 香港电台第一台 (radio1) |
| 播出 | 逢星期六 20:00–20:30 |
| 官网重温 | https://www.rthk.hk/radio/radio1/programme/People |
| Podcast One | https://podcast.rthk.hk/podcast/item.php?pid=287 |
| 官方 RSS（已停更） | https://podcast.rthk.hk/podcast/people.xml |
| 节目 slug | `People`（注意大小写） |
| Podcast pid | `287` |

### 问题现象

- 官方 RSS `people.xml` **停更**，最新一集停在 **2025-09-27**《孫權 (二)︰兩漢楚文化》。
- 官网重温页仍正常更新；截至 2026-07-21，最新为 **2026-07-18**《漢武帝 (六)︰尊崇儒術》。
- 差距约 **10 个月**。
- Castbox / Apple Podcasts / Podcast Republic 等第三方目录均镜像官方 feed，同样停更。
- **未发现**任何仍在维护的非官方替代 RSS。

### 根因（港台政策）

港台 Podcast FAQ 写明：

> 由 **2025 年 10 月**起，港台不再于第三方平台上载完整节目。  
> 欢迎用户透过港台网站（rthk.hk）或港台流动程式重温。

因此 Podcast RSS 停更是**政策结果**，不是偶发故障。音频仍可通过官网「节目重温」收听。

### 用户目标

自托管一份可用的 Podcast RSS：

1. 从官网重温拉取最新集数元数据；
2. 生成标准 Podcast RSS 2.0（含 iTunes 标签）；
3. enclosure 直链港台 CDN 音频（**不下载、不转码、不存音频副本**）；
4. 用户用任意播客客户端订阅该 RSS。

---

## 2. 已验证的数据源

### 2.1 集数列表 API（主数据源）

```
GET https://www.rthk.hk/radio/catchUp?c=radio1&p=People&page=1
```

- 返回 JSON。
- 建议请求头：`User-Agent: Mozilla/5.0`（与浏览器一致即可）。
- 分页：响应含 `"nextPage": 2`；无更多时需实测（可能无 nextPage 或 content 为空）。
- 按月也可：`https://www.rthk.hk/radio/catchUpByMonth?c=radio1&p=People&m=202607`（`m=YYYYMM`）。

**示例响应（节选，已解码）：**

```json
{
  "status": "1",
  "content": [
    {
      "id": "1115200",
      "title": "漢武帝 (六)︰尊崇儒術",
      "message": [],
      "mediaCutOffTime": [],
      "date": "18/07/2026",
      "photos": { "photo": [] },
      "part": ["足本 Full (HKT 20:00 - 20:30)"]
    }
  ],
  "nextPage": 2
}
```

**字段说明：**

| 字段 | 含义 | 用途 |
|------|------|------|
| `id` | 集数 ID | guid、详情页链接 |
| `title` | 标题 | `<title>` |
| `date` | `DD/MM/YYYY` | pubDate、拼音频 URL |
| `part` | 分轨说明 | 本节目通常仅「足本」一轨 |

### 2.2 单集详情（可选，一般不需要）

```
GET https://www.rthk.hk/radio/getEpisode?c=radio1&p=People&e={id}
```

- 返回 **HTML 片段**（非 JSON），含简介、主持人、播放器脚本。
- 实现 RSS 时**不必依赖**此接口；简介可省略或后续再抓。
- 详情页：`https://www.rthk.hk/radio/radio1/programme/People/episode/{id}`

### 2.3 音频直链（enclosure，已验证 200）

**推荐（直接 m4a / mp4 容器，适合 Podcast enclosure）：**

```
https://archive.rthk.hk/mp3/radio/archive/radio1/People/m4a/{YYYYMMDD}.m4a
```

| 检测项 | 结果（2026-07-18 一集） |
|--------|-------------------------|
| URL | `.../People/m4a/20260718.m4a` |
| HTTP | 200 |
| Content-Type | `audio/mp4` |
| Content-Length | `14162828`（约 13.5 MB） |
| Accept-Ranges | bytes |

**日期转换：**

```
API date:  "18/07/2026"   (DD/MM/YYYY)
URL date:  20260718       (YYYYMMDD)
```

伪代码：

```python
# date_str = "18/07/2026"
d, m, y = date_str.split("/")
yyyymmdd = f"{y}{m}{d}"  # "20260718"
audio_url = f"https://archive.rthk.hk/mp3/radio/archive/radio1/People/m4a/{yyyymmdd}.m4a"
```

**备选 HLS（多数播客客户端不支持，勿作 enclosure 主链）：**

```
https://rthkaod2022.akamaized.net/m4a/radio/archive/radio1/People/m4a/{YYYYMMDD}.m4a/master.m3u8
```

### 2.4 封面图

任选其一（均可公网访问）：

```
https://podcast.rthk.hk/podcast/upload_photo/item_photo/1400x1400_287.jpg
https://webstatic.rthk.hk/oldassets/images/rthk/radio1/People/4819_115.jpg
```

### 2.5 官方旧 RSS（仅作元数据/历史参考）

```
https://podcast.rthk.hk/podcast/people.xml
```

- 仍可访问，但内容停在 2025-09-27。
- 可选：P2 阶段合并进自建 feed 作为更早历史（注意与重温 12 个月窗口重叠去重）。

### 2.6 重温保留期

- 官网说明：一般可重温约 **过去 12 个月**（版权限制除外）。
- 更早集数可能 404，生成 feed 时应用 HEAD/GET 探测或捕获失败并跳过。

---

## 3. 方案架构

### 3.1 原则

1. **只生成 RSS 元数据**，音频仍由港台 CDN 提供。
2. **不破解、不批量镜像下载**整站音频做二次分发。
3. 供**个人订阅**使用；注意版权与港台条款。
4. 接口变更时集中改 URL 模板即可。

### 3.2 数据流

```
定时任务（建议：每周六 21:30 HKT，或每天 1 次）
    │
    ▼
分页请求 catchUp API（c=radio1, p=People）
    │
    ▼
解析 id / title / date → 拼 audio URL、详情 link、pubDate
    │
    ▼
（可选）对 enclosure 发 HEAD，取 Content-Length；失败则跳过或 length=0
    │
    ▼
生成 Podcast RSS 2.0 + iTunes 标签 → feed.xml
    │
    ▼
静态托管 / 本机 HTTP / Worker 现算
```

### 3.3 托管选项（实现时三选一或先做 P0）

| 方案 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| A. 本机 | 脚本写 `feed.xml` + `python -m http.server` | 最快验证 | 公网/手机订阅麻烦 |
| B. GitHub Actions + Pages | cron 生成并推送 `feed.xml` | 免费、HTTPS、稳 | 非实时，有调度延迟 |
| C. Cloudflare Worker | 请求时抓 API 生成 RSS，可 KV 缓存 | 公网、较实时 | 需 CF 账号与少量代码 |

**建议落地顺序：** P0 本地脚本验证 → P1 选 B 或 C 上公网。

---

## 4. RSS 规格

### 4.1 Channel 级

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>香港電台：古今風雲人物（重溫）</title>
    <link>https://www.rthk.hk/radio/radio1/programme/People</link>
    <description>介紹古今中外歷史人物……（可用官网简介）。非官方 RSS，音频来自港台节目重温。</description>
    <language>zh-hk</language>
    <itunes:author>RTHK / 香港電台文教組</itunes:author>
    <itunes:summary>...</itunes:summary>
    <itunes:owner>
      <itunes:name>self-hosted</itunes:name>
    </itunes:owner>
    <itunes:image href="https://podcast.rthk.hk/podcast/upload_photo/item_photo/1400x1400_287.jpg"/>
    <itunes:category text="History"/>
    <itunes:explicit>false</itunes:explicit>
    <atom:link href="{你的feed公网URL}" rel="self" type="application/rss+xml"/>
    <!-- items -->
  </channel>
</rss>
```

标题建议带「重溫」或「非官方」，避免与官方 feed 混淆。

### 4.2 Item 级

```xml
<item>
  <title>漢武帝 (六)︰尊崇儒術</title>
  <link>https://www.rthk.hk/radio/radio1/programme/People/episode/1115200</link>
  <guid isPermaLink="false">rthk-people-1115200</guid>
  <pubDate>Sat, 18 Jul 2026 20:00:00 +0800</pubDate>
  <description><![CDATA[可选：从 getEpisode 抽简介，或仅放标题]]></description>
  <enclosure
      url="https://archive.rthk.hk/mp3/radio/archive/radio1/People/m4a/20260718.m4a"
      type="audio/mp4"
      length="14162828"/>
  <!-- itunes:duration 可选；无则省略 -->
</item>
```

**规则：**

| 元素 | 规则 |
|------|------|
| `guid` | 稳定且唯一：`rthk-people-{id}`，勿用会变的 URL 当唯一依据（`isPermaLink="false"`） |
| `pubDate` | RFC 822；播出日周六 20:00 +0800 即可 |
| `enclosure.type` | `audio/mp4`（与 CDN 一致） |
| `enclosure.length` | 优先 HEAD 的 Content-Length；拿不到可用 `0`（部分客户端仍可播） |
| 排序 | 新在前（page=1 已是新→旧，合并多页后保持） |

### 4.3 集数数量

- 默认：拉满 catchUp 能拿到的全部（约 12 个月，周更约 50 集量级）。
- 或配置 `MAX_ITEMS=30` 只保留最新 N 集，减小 feed 体积。

---

## 5. 实现分期

### P0 — 本地可运行（最小可用）

- [ ] 单一脚本（建议 Python 3.10+，标准库优先：`urllib`/`json`/`xml` 或 `email.utils` 格式化日期）。
- [ ] 分页拉取 `catchUp` 直至无更多。
- [ ] 生成 `feed.xml` 到本地路径。
- [ ] 打印最新 3 条 title/date/audio_url 便于人工核对。
- [ ] README：如何运行、如何本地订阅验证。

**验收：**

1. `feed.xml` 通过 XML 解析；
2. 最新 `<item>` 日期与官网重温一致（应 ≥ 2026-07 而非 2025-09）；
3. enclosure URL 浏览器/curl 可 200；
4. 本地播客客户端或 [podba.se](https://podba.se/) 类工具能识别（若环境允许）。

### P1 — 公网订阅

- [ ] 选定托管：GitHub Actions + Pages **或** Cloudflare Worker。
- [ ] HTTPS 稳定 URL，写入 channel 的 `atom:link rel="self"`。
- [ ] 定时更新（GH：`schedule` cron；Worker：Cache-Control / KV TTL，如 1–6 小时）。
- [ ] 失败时保留上一份 feed 或返回明确错误，避免写出空 channel。

### P2 — 可选增强

- [ ] 合并官方旧 `people.xml` 历史项（按 guid/date 去重）。
- [ ] 配置化：支持其他电台节目（`c`/`p`/路径模板）。
- [ ] 抓取 `getEpisode` 简介写入 `<description>`。
- [ ] HEAD 校验音频，404 则标记或排除。
- [ ] 简单变更通知（可选）。

---

## 6. 建议目录与接口（给实现 Agent）

```
rthk-people-rss/
  README.md
  generate_feed.py      # 或 main.py
  feed.xml             # 生成物（可 gitignore 或 Actions 产物）
  requirements.txt     # 若只用标准库可省略或留空说明
```

**建议 CLI：**

```bash
python generate_feed.py --out feed.xml --max-items 0
# --max-items 0 表示不限制；30 表示最新 30 集
```

**核心函数建议：**

1. `fetch_episodes(channel, programme) -> list[dict]`
2. `date_to_yyyymmdd(dd_mm_yyyy) -> str`
3. `audio_url(programme, yyyymmdd) -> str`
4. `build_rss(episodes, feed_self_url) -> str`
5. `main()`

**错误处理：**

- HTTP 非 200 / JSON 无 content：退出非零并 stderr 说明。
- 单集音频 HEAD 404：跳过该集并 warning，不中断整次生成。
- 空列表：不要覆盖已有 `feed.xml`（P1）；P0 可报错退出。

---

## 7. 风险与限制

| 风险 | 说明 | 缓解 |
|------|------|------|
| API 变更 | catchUp 路径或字段改名 | 集中配置 BASE_URL 与字段映射 |
| 音频路径变更 | CDN 域名/目录调整 | 模板常量 + 单集探测 |
| 重温过期 | 约 12 个月后 404 | HEAD 过滤；guid 稳定以免客户端混乱 |
| `audio/mp4` 兼容性 | 极少数老客户端不认 m4a | 文档说明；一般 AntennaPod/Apple/现代客户端可播 |
| 版权/ToS | 港台内容，第三方分发敏感 | 仅个人自托管元数据；不二次上传音频到公共镜像站 |
| 政策再收紧 | 重温改登录墙/防盗链 | 需重新评估，当前无鉴权直链可用 |

---

## 8. 验证用样例数据（2026-07-21 实测）

| 来源 | 最新标题 | 日期 |
|------|----------|------|
| 官方 RSS people.xml | 孫權 (二)︰兩漢楚文化 | 2025-09-27 |
| catchUp page=1 | 漢武帝 (六)︰尊崇儒術 | 2026-07-18 |
| 音频 | `.../20260718.m4a` | 200, audio/mp4, 14162828 bytes |

**样例 enclosure：**

```
https://archive.rthk.hk/mp3/radio/archive/radio1/People/m4a/20260718.m4a
```

**样例详情页：**

```
https://www.rthk.hk/radio/radio1/programme/People/episode/1115200
```

**catchUp 最新若干集（便于对账）：**

1. 1115200 — 漢武帝 (六)︰尊崇儒術 — 18/07/2026  
2. 1112317 — 漢武帝 (五)︰衛子夫封后 — 11/07/2026  
3. 1110801 — 漢武帝 (四)︰反擊匈奴 — 04/07/2026  
4. 1110720 — 漢武帝 (三)︰武帝登位 — 27/06/2026  
5. 1109239 — 漢武帝 (二)︰劉徹出身 — 20/06/2026  

实现完成后，feed 第一条应与上表第 1 条一致（若官网此后有更新，则以 API 实时结果为准，但**绝不能**仍停在 2025-09）。

---

## 9. 明确不在范围内

- 不修复/不依赖官方 `people.xml` 恢复更新。
- 不爬 Podcast One 的 `episodeList.php` 作为主源（该源与官方 RSS 同步停更）。
- 不实现完整港台全台节目站（除非 P2 配置化扩展）。
- 不提供大规模公开转载/商业分发方案。

---

## 10. 给执行 Agent 的一句话任务

> 编写 Python 脚本：分页请求 `https://www.rthk.hk/radio/catchUp?c=radio1&p=People&page=N`，将每集转为 Podcast RSS item，enclosure 使用 `https://archive.rthk.hk/mp3/radio/archive/radio1/People/m4a/{YYYYMMDD}.m4a`，输出 `feed.xml`；验收标准为最新集日期与官网重温一致且明显新于 2025-09-27。

---

## 11. 参考链接速查

```
重温页:     https://www.rthk.hk/radio/radio1/programme/People
列表 API:   https://www.rthk.hk/radio/catchUp?c=radio1&p=People&page=1
按月 API:   https://www.rthk.hk/radio/catchUpByMonth?c=radio1&p=People&m=YYYYMM
音频模板:   https://archive.rthk.hk/mp3/radio/archive/radio1/People/m4a/{YYYYMMDD}.m4a
HLS 备选:   https://rthkaod2022.akamaized.net/m4a/radio/archive/radio1/People/m4a/{YYYYMMDD}.m4a/master.m3u8
官方 RSS:   https://podcast.rthk.hk/podcast/people.xml
Podcast页:  https://podcast.rthk.hk/podcast/item.php?pid=287
封面:       https://podcast.rthk.hk/podcast/upload_photo/item_photo/1400x1400_287.jpg
```
