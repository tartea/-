# 股票 · 每日复盘归档

本目录是 `stock-daily` 技能的产物区。**每个交易日一个目录**，根目录 `index.json` 是跨日索引。
2026-10-21 ~ 2026-11-04 已连续覆盖（中间无缺口）。

## 结构

```
股票/
├── index.json                 跨日索引（技能脚本维护）
├── README.md                  本文件
├── <YYYY-MM-DD>/
│   ├── report.json            唯一机器可读真源（schema v1.0）
│   └── report.html            人读版（自包含，零外部依赖）
├── analysis/                  归因分析（跨日统计，非每日产物）
├── 2026-10-21/                legacy 目录（详见口径说明 1）
└── quantify/                  潮位（Quantify）MCP 历史归档，非本技能产物
```

## 覆盖情况

| 日期 | 格式 | 闸门 | 情绪 | 名单数 | 产物 | 备注 |
|---|---|---|---|---|---|---|
| 2026-10-21 | legacy | — | 分歧 | 5 | result.json+html+md | R-DATA-05 之前的旧格式，原样保留 |
| 2026-10-22 | v1.0 | 空仓 | 退潮 | 5 | report.json+html |  |
| 2026-10-23 | v1.0 | 正常 | 修复 | 5 | report.json+html |  |
| 2026-10-26 | v1.0 | 半仓 | 分歧 | 5 | report.json+html |  |
| 2026-10-27 | v1.0 | 空仓 | 退潮 | 3 | report.json+html | v1.23 本地重建 |
| 2026-10-28 | v1.0 | 空仓 | 分歧 | 5 | report.json+html | v1.23 本地重建 |
| 2026-10-29 | v1.0 | 空仓 | 退潮 | 1 | report.json+html | v1.23 本地重建 |
| 2026-10-30 | v1.0 | 空仓 | 退潮 | 4 | report.json+html | v1.23 本地重建 |
| 2026-11-02 | v1.0 | 半仓 | 分歧 | 0 | report.json+html | 从 quantify 导入（规则 1.21）；名单为空 |
| 2026-11-03 | v1.0 | 空仓 | 退潮 | 5 | report.json+html | 从 quantify 导入（规则 1.22） |
| 2026-11-04 | v1.0 | 半仓 | 分歧 | 5 | report.json+html | 本地生成 |

## 口径说明

1. **10-21 是 legacy 格式**：当时管线还产出 `analysis.md` + `result.json`，R-DATA-05 之后改为「只产出 report.json + report.html」。
   该日无 `.cache/run-2026-10-21.json`，无法按新管线重算，故原样保留，索引里标 `format: legacy`。
2. **10-27 ~ 10-30 于 2026-11-04 本地重建**：原始报告已从工作区丢失且未提交 git，只剩 `.cache/` 的取数结果与叙述侧车，
   因此用现行 v1.23 规则重跑 `build.py` + `render.py`。闸门档位与名单与当时一致，个别分数随规则演进有微调
   （例：10-27 凯中精密由当时记录的 68 分变为 61 分）。`RULES.md` §9/§10 保留当日发布记录，两者不一致时以报告为准。
3. **10-21 ~ 10-26 从 git 原样恢复**，未重算，分数保持发布时状态。
4. **11-02 / 11-03 从 quantify 导入**：本地从未跑过这两天，无 `.cache/run-<date>.json`，无法在本地重建。
   `report.json` 取自潮位服务端产出的记录（同为 `schema: stock-daily.report` v1.0），`report.html` 由本地 `render.py` 渲染。
   - 11-02：v1，2026-11-02 20:33 生成，规则 1.21。当日池 114 → 过硬门槛 2 只，但 **55 / 44 分均未达 R-SCORE-04 的 60 分线，名单为空**，
     回填 10-30 名单 1/4。
   - 11-03：v2，2026-11-03 21:11 生成，规则 1.22。闸门空仓（炸板率 41.5%、晋级率 12.9%），名单 5 只，
     但因为 11-02 名单为空，它的 `review` 无可回填对象（报告里如实显示为空）。
   - 这两天**未写入** `RULES.md` §9/§10——规则库只记录本地实际执行过的复盘。
5. **11-04 的回填已接上 11-03**：1/5 晋级（大连友谊 +9.97% 二板），其余 4 只归因「板块」——
   电池 7→0 家、一般零售 4→0 家，题材全部掉出主线。
6. **`quantify/` 不属于本技能**：潮位 MCP 的历史归档（`daily/ now/ stock/` + 自己的 `index.json` + `sync.py`），
   格式与 `report.json` 无关，不要混入 `index.json`。

## 复现与维护

```bash
SD=.dsh/skills/stock-daily/scripts
python3 $SD/fetch.py   --date YYYY-MM-DD --root /Users/ali/Documents/stock   # 取数 → .cache/run-<date>.json
#   写叙述 → .cache/narrative-<date>.json
python3 $SD/build.py   --date YYYY-MM-DD --root /Users/ali/Documents/stock   # → <date>/report.json + index.json
python3 $SD/render.py  --date YYYY-MM-DD --root /Users/ali/Documents/stock   # → <date>/report.html
```

两个已知坑：

- `build.py` 的「昨日回填」取的是**日期最近的一份报告**，不做交易日相邻校验。重跑某天时若它前面有整段缺失，
  会错配到更早一天的名单——需先把更早的日期目录临时移开。
- `update_index()` 会跳过「已有 report.json 但不在索引里」的目录，且会按 `result.json` 重算 legacy 行。
  手工导入某天的报告后，需单独调用 `build.update_index(root, report, review)` 补索引。

## analysis/

跨日归因分析文档。首篇：[2026-11-04-一进二失败率归因.md](analysis/2026-11-04-一进二失败率归因.md)——
38 个回填样本的失败率拆解、规则体检与新增规则依据。
