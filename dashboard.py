#!/usr/bin/env python3
"""Build a self-contained HTML dashboard from k6 + pod-monitor outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _read_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def _iter_ndjson(path: Path) -> Iterable[dict]:
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def find_latest(dir_path: Path, patterns: List[str]) -> Optional[Path]:
    matches: List[Path] = []
    for pattern in patterns:
        matches.extend(dir_path.glob(pattern))
        matches.extend(dir_path.glob(f"**/{pattern}"))
    files = [p for p in matches if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def find_all(dir_path: Path, patterns: List[str]) -> List[Path]:
    matches: List[Path] = []
    for pattern in patterns:
        matches.extend(dir_path.glob(pattern))
        matches.extend(dir_path.glob(f"**/{pattern}"))
    files = [p for p in matches if p.is_file()]
    return sorted(set(files), key=lambda p: p.stat().st_mtime)


def metric_values(summary: dict, name: str) -> dict:
    metrics = summary.get("metrics") or {}
    entry = metrics.get(name) or {}
    return entry.get("values") or {}


def parse_k6_summary(path: Path) -> Dict[str, Any]:
    summary = _read_json(path)
    duration = metric_values(summary, "http_req_duration")
    reqs = metric_values(summary, "http_reqs")
    failed = metric_values(summary, "http_req_failed")
    waiting = metric_values(summary, "http_req_waiting")
    return {
        "file": path.name,
        "count": reqs.get("count"),
        "rate": reqs.get("rate"),
        "fail_rate": failed.get("rate"),
        "avg_ms": duration.get("avg"),
        "med_ms": duration.get("med"),
        "p90_ms": duration.get("p(90)") or duration.get("p90"),
        "p95_ms": duration.get("p(95)") or duration.get("p95"),
        "p99_ms": duration.get("p(99)") or duration.get("p99"),
        "max_ms": duration.get("max"),
        "waiting_avg_ms": waiting.get("avg"),
        "raw": summary,
    }


def _iso_to_epoch(ts: str) -> Optional[float]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return None


def parse_k6_raw(path: Path, max_points: int = 400) -> Dict[str, Any]:
    latency: List[Tuple[float, float, str]] = []
    statuses: Dict[str, int] = {}
    for point in _iter_ndjson(path):
        if point.get("type") != "Point":
            continue
        data = point.get("data") or {}
        tags = data.get("tags") or {}
        metric = point.get("metric")
        if metric == "http_req_duration":
            ts = _iso_to_epoch(data.get("time") or "")
            value = data.get("value")
            if ts is None or value is None:
                continue
            latency.append((ts, float(value), str(tags.get("status", "unknown"))))
        elif metric == "http_reqs":
            status = str(tags.get("status", "unknown"))
            statuses[status] = statuses.get(status, 0) + 1

    latency.sort(key=lambda row: row[0])
    sampled = _downsample(latency, max_points)
    buckets: Dict[int, List[float]] = {}
    for ts, value, _status in latency:
        key = int(ts // 10 * 10)
        buckets.setdefault(key, []).append(value)
    p95_series = []
    for key in sorted(buckets):
        vals = sorted(buckets[key])
        p95_series.append((key, _percentile(vals, 0.95), _percentile(vals, 0.50)))
    p95_series = _downsample(p95_series, max_points)

    return {
        "file": path.name,
        "latency": sampled,
        "p95": p95_series,
        "statuses": statuses,
        "count": len(latency),
    }


def _percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    idx = min(len(values) - 1, max(0, int(math.ceil(q * len(values)) - 1)))
    return values[idx]


def _downsample(rows: list, max_points: int) -> list:
    if len(rows) <= max_points:
        return rows
    step = max(1, len(rows) // max_points)
    sampled = rows[::step]
    if sampled[-1] != rows[-1]:
        sampled.append(rows[-1])
    return sampled[:max_points]


def parse_pod_csv(path: Path) -> Dict[str, Any]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return {"file": path.name, "series": {}, "cpu_col": None, "mem_col": None}

    cpu_col = _first_col(rows[0], ["CPU_Value", "CPU", "cpu", "CPU_millicores"])
    mem_col = _first_col(rows[0], ["Memory_Value_Gi", "Memory_Gi", "memory_gi", "Memory"])
    ts_col = _first_col(rows[0], ["Timestamp", "timestamp", "Time"])
    name_col = _first_col(rows[0], ["Container", "Pod", "pod", "Name"])

    series: Dict[str, List[Tuple[str, float, float]]] = {}
    for row in rows:
        name = row.get(name_col) or "pod" if name_col else "pod"
        ts = row.get(ts_col) or "" if ts_col else ""
        cpu = _to_float(row.get(cpu_col) if cpu_col else None)
        mem = _to_float(row.get(mem_col) if mem_col else None)
        series.setdefault(name, []).append((ts, cpu or 0.0, mem or 0.0))

    return {
        "file": path.name,
        "series": series,
        "cpu_col": cpu_col,
        "mem_col": mem_col,
        "count": len(rows),
    }


def _first_col(row: dict, names: List[str]) -> Optional[str]:
    for name in names:
        if name in row:
            return name
    lower = {k.lower(): k for k in row}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def render_html(report: Dict[str, Any]) -> str:
    payload = json.dumps(report, default=str)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    datadog = report.get("datadog") or ""
    datadog_link = (
        f'<a class="dd" href="{datadog}" target="_blank" rel="noreferrer">Open Datadog dashboard</a>'
        if datadog
        else ""
    )
    k6 = report.get("k6") or {}
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{report.get("title")}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #111318;
      --card: #1b1e27;
      --text: #e8eaed;
      --muted: #9aa0a6;
      --line: #2a2f3a;
      --accent: #7aa2f7;
      --ok: #9ece6a;
      --warn: #e0af68;
      --bad: #f7768e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 14px/1.45 ui-sans-serif, system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    header {{
      padding: 24px 28px 8px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 6px; font-size: 22px; font-weight: 600; }}
    .sub {{ color: var(--muted); }}
    .dd {{ color: var(--accent); }}
    main {{ padding: 20px 28px 48px; max-width: 1100px; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      margin: 20px 0;
    }}
    .stat {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
    }}
    .stat b {{ display: block; font-size: 22px; font-weight: 600; }}
    .stat span {{ color: var(--muted); font-size: 12px; }}
    .bad b {{ color: var(--bad); }}
    .ok b {{ color: var(--ok); }}
    section {{ margin: 28px 0; }}
    h2 {{ font-size: 16px; font-weight: 600; margin: 0 0 12px; }}
    svg {{ width: 100%; height: 240px; background: var(--card); border: 1px solid var(--line); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); }}
    th {{ color: var(--muted); font-weight: 500; font-size: 12px; }}
    .empty {{ color: var(--muted); padding: 12px 0; }}
    caption {{ caption-side: bottom; color: var(--muted); font-size: 12px; text-align: left; padding-top: 8px; }}
  </style>
</head>
<body>
  <header>
    <h1>{report.get("title")}</h1>
    <div class="sub">{report.get("service")} · {report.get("region")} · generated {generated}</div>
    {datadog_link}
  </header>
  <main>
    <div class="stats" id="stats"></div>
    <section>
      <h2>k6 latency over time (ms)</h2>
      <svg id="latency" role="img" aria-label="Request latency over time in milliseconds"></svg>
    </section>
    <section>
      <h2>HTTP status codes</h2>
      <table id="statuses"><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody></tbody>
      <caption>Source: k6 NDJSON http_reqs · file {k6.get("raw_file") or k6.get("file") or "—"}</caption>
      </table>
    </section>
    <section>
      <h2>Pod CPU</h2>
      <svg id="cpu" role="img" aria-label="Pod CPU usage over time"></svg>
    </section>
    <section>
      <h2>Pod memory</h2>
      <svg id="mem" role="img" aria-label="Pod memory usage over time"></svg>
    </section>
  </main>
  <script id="report" type="application/json">{payload}</script>
  <script>
    const report = JSON.parse(document.getElementById("report").textContent);
    const k6 = report.k6 || {{}};
    const fail = k6.fail_rate || 0;
    const stats = [
      ["Requests", fmt(k6.count, 0), ""],
      ["Achieved RPS", fmt(k6.rate, 1), ""],
      ["Error rate", pct(fail), fail > 0.05 ? "bad" : "ok"],
      ["Avg latency", ms(k6.avg_ms), ""],
      ["P95", ms(k6.p95_ms), ""],
      ["P99", ms(k6.p99_ms), ""],
    ];
    document.getElementById("stats").innerHTML = stats.map(([label, value, cls]) =>
      `<div class="stat ${{cls}}"><b>${{value}}</b><span>${{label}}</span></div>`
    ).join("");

    const statusBody = document.querySelector("#statuses tbody");
    const statuses = (report.raw && report.raw.statuses) || {{}};
    const statusRows = Object.entries(statuses).sort((a,b) => b[1]-a[1]);
    if (!statusRows.length) {{
      statusBody.innerHTML = `<tr><td colspan="2" class="empty">No status samples in raw k6 output</td></tr>`;
    }} else {{
      statusBody.innerHTML = statusRows.map(([code, n]) => `<tr><td>${{code}}</td><td>${{n}}</td></tr>`).join("");
    }}

    drawLine("latency", (report.raw && report.raw.latency) || [], 1, "ms");
    drawPod("cpu", report.pods || [], 1);
    drawPod("mem", report.pods || [], 2);

    function fmt(v, d) {{
      if (v === undefined || v === null || v === "—") return "—";
      const n = Number(v);
      if (!Number.isFinite(n)) return "—";
      return n.toLocaleString(undefined, {{ maximumFractionDigits: d }});
    }}
    function ms(v) {{ return v === undefined || v === null ? "—" : fmt(v, 1) + " ms"; }}
    function pct(v) {{ return v === undefined || v === null ? "—" : (Number(v)*100).toFixed(2) + "%"; }}

    function drawLine(id, rows, valueIndex, _unit) {{
      const svg = document.getElementById(id);
      if (!rows.length) {{ emptySvg(svg, "No k6 time series"); return; }}
      const xs = rows.map(r => r[0]);
      const ys = rows.map(r => r[valueIndex]);
      plot(svg, xs, [ys], ["latency"]);
    }}

    function drawPod(id, pods, valueIndex) {{
      const svg = document.getElementById(id);
      const names = [];
      const series = [];
      const xsAll = [];
      for (const pod of pods) {{
        for (const [name, points] of Object.entries(pod.series || {{}})) {{
          names.push(name);
          const xs = points.map((p, i) => i);
          const ys = points.map(p => p[valueIndex]);
          series.push(ys);
          if (xs.length > xsAll.length) {{
            xsAll.length = 0;
            xs.forEach(x => xsAll.push(x));
          }}
        }}
      }}
      if (!series.length) {{ emptySvg(svg, "No pod CSV in this report directory"); return; }}
      plot(svg, xsAll, series, names);
    }}

    function emptySvg(svg, msg) {{
      svg.innerHTML = `<text x="16" y="32" fill="#9aa0a6">${{msg}}</text>`;
    }}

    function plot(svg, xs, seriesList, names) {{
      const w = 1000, h = 240, pad = 36;
      let minY = Infinity, maxY = -Infinity;
      seriesList.forEach(s => s.forEach(v => {{ minY = Math.min(minY, v); maxY = Math.max(maxY, v); }}));
      if (minY === maxY) {{ maxY = minY + 1; }}
      const minX = Math.min(...xs), maxX = Math.max(...xs);
      const sx = x => pad + (x - minX) / Math.max(1e-9, maxX - minX) * (w - pad * 2);
      const sy = y => h - pad - (y - minY) / (maxY - minY) * (h - pad * 2);
      const colors = ["#7aa2f7", "#9ece6a", "#e0af68", "#bb9af7", "#f7768e", "#7dcfff"];
      let paths = seriesList.map((s, i) => {{
        const d = s.map((y, idx) => `${{idx ? "L" : "M"}} ${{sx(xs[Math.min(idx, xs.length-1)]).toFixed(1)}} ${{sy(y).toFixed(1)}}`).join(" ");
        return `<path d="${{d}}" fill="none" stroke="${{colors[i % colors.length]}}" stroke-width="1.6" />`;
      }}).join("");
      const legend = names.slice(0, 6).map((n, i) =>
        `<text x="${{pad + i * 140}}" y="18" fill="${{colors[i % colors.length]}}" font-size="11">${{n}}</text>`
      ).join("");
      svg.setAttribute("viewBox", `0 0 ${{w}} ${{h}}`);
      svg.innerHTML = `${{legend}}${{paths}}<text x="${{pad}}" y="${{h-8}}" fill="#9aa0a6" font-size="11">${{fmt(minY,1)}} – ${{fmt(maxY,1)}}</text>`;
    }}
  </script>
</body>
</html>
"""


def build_report(
    directory: Path,
    service: str,
    region: str,
    datadog: str = "",
    summary_path: Optional[Path] = None,
    raw_path: Optional[Path] = None,
    csv_paths: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    summary_path = summary_path or find_latest(directory, ["*summary.json", "*stress-test-summary.json"])
    raw_path = raw_path or find_latest(directory, ["*raw-data.json", "*raw.json", "*stress-test-raw.json"])
    csv_paths = csv_paths or find_all(directory, ["*.csv"])

    k6: Dict[str, Any] = {}
    raw: Dict[str, Any] = {}
    if summary_path:
        k6 = parse_k6_summary(summary_path)
    if raw_path:
        raw = parse_k6_raw(raw_path)
        k6["raw_file"] = raw_path.name
        if not k6.get("count") and raw.get("count"):
            k6["count"] = raw["count"]
        if k6.get("avg_ms") is None and raw.get("latency"):
            values = [row[1] for row in raw["latency"]]
            k6["avg_ms"] = statistics.mean(values)
            k6["p95_ms"] = _percentile(sorted(values), 0.95)
            k6["p99_ms"] = _percentile(sorted(values), 0.99)

    pods = [parse_pod_csv(path) for path in csv_paths]
    title = f"{service} holiday test — {region}"
    return {
        "title": title,
        "service": service,
        "region": region,
        "datadog": datadog,
        "k6": k6,
        "raw": raw,
        "pods": pods,
        "files": {
            "summary": summary_path.name if summary_path else None,
            "raw": raw_path.name if raw_path else None,
            "csv": [p.name for p in csv_paths],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate holiday-test HTML dashboard")
    parser.add_argument("--dir", default=".", help="Directory containing k6/monitor outputs")
    parser.add_argument("--service", default="unknown")
    parser.add_argument("--region", default="unknown")
    parser.add_argument("--datadog", default="")
    parser.add_argument("--k6-summary")
    parser.add_argument("--k6-raw")
    parser.add_argument("--pod-csv", action="append", default=[])
    parser.add_argument("-o", "--out", help="Output HTML path (default: DIR/index.html)")
    args = parser.parse_args()

    directory = Path(args.dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    report = build_report(
        directory=directory,
        service=args.service,
        region=args.region,
        datadog=args.datadog,
        summary_path=Path(args.k6_summary) if args.k6_summary else None,
        raw_path=Path(args.k6_raw) if args.k6_raw else None,
        csv_paths=[Path(p) for p in args.pod_csv] if args.pod_csv else None,
    )
    out = Path(args.out) if args.out else directory / "index.html"
    out.write_text(render_html(report), encoding="utf-8")
    print(f"Wrote {out}")
    if not report["files"]["summary"] and not report["files"]["raw"]:
        print("warning: no k6 summary/raw files found — dashboard will be mostly empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
