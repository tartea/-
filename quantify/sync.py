#!/usr/bin/env python3
"""把潮位（Quantify）的全部历史记录导出到 股票/quantify/。

布局：
  quantify/index.json          机器索引（逐条记录元信息 + 结论）
  quantify/index.md            人读索引
  quantify/daily/<date>-v<n>.json         每日复盘（含 report 全节，无损）
  quantify/daily/<date>-v<n>.html         官方渲染版（仅 daily 有）
  quantify/now/<date>-v<n>.json           此刻分析
  quantify/stock/<date>-<code>-v<n>.json  单票诊断
  quantify/stock/<date>-<code>-v<n>.md    单票诊断可读版
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

PATCH = "/Users/ali/Library/Application Support/dsh-desktop/harness/profiles/web/cordis.patch.yml"
ROOT = "/Users/ali/Documents/stock/股票/quantify"

with open(PATCH, encoding="utf-8") as f:
    text = f.read()
BASE = re.search(r"QUANTIFY_BASE_URL:\s*(\S+)", text).group(1).rstrip("/")
TOKEN = re.search(r"QUANTIFY_TOKEN:\s*(\S+)", text).group(1)


def api(path: str):
    """返回 (status, bytes)。状态非 200 时字节是错误体。"""
    req = urllib.request.Request(BASE + path, headers={"authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def jget(path: str):
    st, body = api(path)
    if st != 200:
        raise SystemExit(f"GET {path} -> {st}: {body[:200]!r}")
    return json.loads(body)


records = jget("/api/records?all=1&limit=200")
if not isinstance(records, list):
    raise SystemExit(f"unexpected payload: {type(records)}")
print(f"记录总数: {len(records)}")

for sub in ("daily", "now", "stock"):
    os.makedirs(os.path.join(ROOT, sub), exist_ok=True)

index = []
written = 0
html_written = 0
failed = []

for n, meta in enumerate(sorted(records, key=lambda r: (r["tradeDate"], r["kind"], r["version"])), 1):
    rid = meta["id"]
    kind = meta["kind"]
    date = meta["tradeDate"]
    ver = meta.get("version") or 1
    code = meta.get("target")

    st, body = api(f"/api/records/{rid}?include=report")
    if st != 200:
        failed.append((rid, f"record {st}"))
        print(f"[{n:2}/{len(records)}] ✗ {kind} {date} {rid[:8]} -> {st}")
        continue

    if kind == "stock" and code:
        stem = f"{date}-{code}-v{ver}"
        sub = "stock"
    else:
        stem = f"{date}-v{ver}"
        sub = kind

    json_path = os.path.join(ROOT, sub, stem + ".json")
    with open(json_path, "wb") as f:
        f.write(body)
    written += 1

    # 官方 HTML 只有每日复盘才有；其余返回 404，静默跳过。
    hst, hbody = api(f"/api/records/{rid}/html?surface=web")
    has_html = hst == 200 and len(hbody) > 1000
    if has_html:
        with open(os.path.join(ROOT, "daily", stem + ".html"), "wb") as f:
            f.write(hbody)
        html_written += 1

    rec = json.loads(body)
    payload = rec.get("payload") or {}
    summary = rec.get("summary") or {}

    # 单票诊断 / 此刻分析：顺手出一份可读 md。
    if kind in ("stock", "now") and isinstance(payload, dict) and payload:
        md = os.path.join(ROOT, sub, stem + ".md")
        snap = payload.get("snapshot") or {}
        quote = snap.get("quote") or {}
        lines = [
            f"# {summary.get('name') or code or '此刻分析'}（{code or '—'}） · {date}",
            "",
            f"- 类型：{kind} v{ver}",
            f"- 生成时间：{rec.get('generatedAt')}",
            f"- 基调：{payload.get('tone') or rec.get('mood')}",
            f"- 结论：{payload.get('verdict') or rec.get('headline')}",
            "",
        ]
        for label, key in (("买点", "buy_zone"), ("止损", "stop"), ("失效", "invalidation")):
            if payload.get(key):
                lines += [f"## {label}", "", payload[key], ""]
        if quote:
            lines += ["## 快照", "", "| 项 | 值 |", "| --- | --- |"]
            for k, v in quote.items():
                cell = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
                lines.append(f"| {k} | {cell} |")
            lines.append("")
        for label, key in (("风险", "risks"), ("理由", "reasons")):
            vals = payload.get(key) or []
            if vals:
                lines += [f"## {label}", ""] + [f"- {v}" for v in vals] + [""]
        with open(md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    index.append(
        {
            "id": rid,
            "kind": kind,
            "tradeDate": date,
            "version": ver,
            "target": code,
            "name": summary.get("name"),
            "generatedAt": rec.get("generatedAt"),
            "gate": rec.get("gate"),
            "mood": rec.get("mood"),
            "headline": rec.get("headline"),
            "file": f"{sub}/{stem}.json",
            "html": f"daily/{stem}.html" if has_html else None,
            "bytes": len(body),
        }
    )
    print(f"[{n:2}/{len(records)}] ✓ {kind:<5} {date} {stem:<28} {len(body)//1024:>4}KB html={'y' if has_html else '-'}")

with open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8") as f:
    json.dump(
        {
            "source": BASE,
            "exportedAt": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
            "count": len(index),
            "records": index,
        },
        f,
        ensure_ascii=False,
        indent=2,
    )

rows = ["| 日期 | 类型 | 标的 | 结论 | 文件 |", "| --- | --- | --- | --- | --- |"]
for r in sorted(index, key=lambda x: (x["tradeDate"], x["kind"], x["version"]), reverse=True):
    label = {"daily": "每日复盘", "now": "此刻分析", "stock": "单票诊断"}[r["kind"]]
    tgt = r["name"] and f"{r['name']} {r['target']}" or (r["target"] or "—")
    head = (r["headline"] or "").replace("|", "\\|")[:46]
    rows.append(f"| {r['tradeDate']} | {label} v{r['version']} | {tgt} | {head} | `{r['file']}` |")

with open(os.path.join(ROOT, "index.md"), "w", encoding="utf-8") as f:
    f.write("# 潮位（Quantify）历史分析归档\n\n")
    f.write(f"- 来源：`{BASE}`\n- 导出时间：见 index.json\n- 记录数：{len(index)}\n\n")
    f.write("每日复盘落在 `daily/`（JSON 无损 + 官方 HTML），单票诊断 / 此刻分析落在 `stock/`、`now/`。\n\n")
    f.write("\n".join(rows) + "\n")

print(f"\n完成：{written} 条 JSON，{html_written} 份 HTML，失败 {len(failed)}")
for rid, why in failed:
    print("  ✗", rid, why)
sys.exit(0 if not failed else 1)
