#!/usr/bin/env python3
"""Holiday-test service catalog. Source of truth: services.yaml."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "services.yaml"

_LIST_FIELDS = {
    "aliases",
    "containers",
    "algo_labels",
}


class CatalogError(Exception):
    pass


def load_catalog(path: Path = CATALOG_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise CatalogError(f"Catalog not found: {path}")
    if path.suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise CatalogError("PyYAML is required. pip install pyyaml")
        with path.open() as f:
            data = yaml.safe_load(f) or {}
    else:
        with path.open() as f:
            data = json.load(f)
    if "services" not in data:
        raise CatalogError("services.yaml is missing a top-level 'services' map")
    return data


def _defaults(catalog: Dict[str, Any]) -> Dict[str, Any]:
    return dict(catalog.get("defaults") or {})


def list_ids(catalog: Optional[Dict[str, Any]] = None) -> List[str]:
    catalog = catalog or load_catalog()
    return sorted(catalog["services"].keys())


def resolve_id(name: str, catalog: Optional[Dict[str, Any]] = None) -> str:
    catalog = catalog or load_catalog()
    key = name.strip()
    services = catalog["services"]
    if key in services:
        return key
    lowered = key.lower()
    for sid, cfg in services.items():
        if sid.lower() == lowered:
            return sid
        aliases = cfg.get("aliases") or []
        if any(str(a).lower() == lowered for a in aliases):
            return sid
        if str(cfg.get("k8s_service", "")).lower() == lowered:
            return sid
        if str(cfg.get("demo_deployment", "")).lower() == lowered:
            return sid
        if str(cfg.get("app_label", "")).lower() == lowered:
            return sid
    known = ", ".join(list_ids(catalog))
    raise CatalogError(f"Unknown service '{name}'. Known: {known}")


def get_service(name: str, catalog: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    catalog = catalog or load_catalog()
    sid = resolve_id(name, catalog)
    defaults = _defaults(catalog)
    cfg = dict(defaults)
    cfg.update(catalog["services"][sid] or {})
    cfg["id"] = sid
    cfg["aliases"] = list(catalog["services"][sid].get("aliases") or [])
    log_regions = dict(defaults.get("log_regions") or {})
    log_regions.update(catalog["services"][sid].get("log_regions") or {})
    cfg["log_regions"] = log_regions
    if not cfg.get("k6_load_script"):
        cfg["k6_load_script"] = defaults.get("k6_load_script", "reranker-load-test.js")
    if not cfg.get("k6_stress_script"):
        cfg["k6_stress_script"] = defaults.get("k6_stress_script", "reranker-stress-test.js")
    if not cfg.get("s3_prefix"):
        cfg["s3_prefix"] = f"{sid}loadtest"
    if not cfg.get("log_prefix"):
        cfg["log_prefix"] = sid
    if not cfg.get("app_label"):
        cfg["app_label"] = cfg.get("k8s_service") or cfg.get("demo_deployment") or sid
    if not cfg.get("k8s_service"):
        cfg["k8s_service"] = cfg.get("demo_deployment") or cfg.get("app_label") or sid
    cfg["algo_labels"] = list(cfg.get("algo_labels") or [])
    cfg["containers"] = list(cfg.get("containers") or [])
    cfg["s3_bucket"] = cfg.get("s3_bucket") or defaults.get("s3_bucket", "unbxd-des")
    return cfg


def log_region_for(cfg: Dict[str, Any], region: str) -> str:
    mapping = cfg.get("log_regions") or {}
    return str(mapping.get(region, region))


def logs_dir(cfg: Dict[str, Any], region: str) -> str:
    return f"{cfg['log_prefix']}-{log_region_for(cfg, region)}-logs"


def s3_results_uri(cfg: Dict[str, Any], region: Optional[str] = None) -> str:
    prefix = cfg["s3_prefix"]
    bucket = cfg["s3_bucket"]
    if region:
        return f"s3://{bucket}/{prefix}/{log_region_for(cfg, region)}/"
    return f"s3://{bucket}/{prefix}/"


def s3_logs_uri(cfg: Dict[str, Any], region: str) -> str:
    return f"s3://{cfg['s3_bucket']}/{cfg['log_prefix']}loadtest-{log_region_for(cfg, region)}/"


def env_map(name: str, region: Optional[str] = None) -> Dict[str, str]:
    cfg = get_service(name)
    log_region = log_region_for(cfg, region) if region else ""
    values = {
        "SERVICE_ID": cfg["id"],
        "SERVICE_DISPLAY": str(cfg.get("display_name") or cfg["id"]),
        "K8S_SERVICE": str(cfg.get("k8s_service") or ""),
        "PROD_DEPLOYMENT": str(cfg.get("prod_deployment") or ""),
        "DEMO_DEPLOYMENT": str(cfg.get("demo_deployment") or ""),
        "NAMESPACE": str(cfg.get("namespace") or "default"),
        "CONTAINERS": ",".join(cfg.get("containers") or []),
        "APP_LABEL": str(cfg.get("app_label") or ""),
        "ALGO_LABELS": ",".join(cfg.get("algo_labels") or []),
        "EXTRACT_SCRIPT": str(cfg.get("extract_script") or ""),
        "LOG_PREFIX": str(cfg["log_prefix"]),
        "PRE_TEST_SYNC": "true" if cfg.get("pre_test_sync") else "false",
        "EXTRA_PRE_TEST": str(cfg.get("extra_pre_test") or ""),
        "S3_BUCKET_NAME": str(cfg["s3_bucket"]),
        "S3_PREFIX": str(cfg["s3_prefix"]),
        "S3_BUCKET": s3_results_uri(cfg, region) if region else s3_results_uri(cfg),
        "S3_LOGS_URI": s3_logs_uri(cfg, region) if region else "",
        "PAYLOAD_MODE": str(cfg.get("payload_mode") or "jsonl"),
        "K6_SCRIPT": str(cfg.get("k6_load_script") or ""),
        "K6_STRESS_SCRIPT": str(cfg.get("k6_stress_script") or ""),
        "FIXTURE": str(cfg.get("fixture") or ""),
        "RUNNER": str(cfg.get("runner") or ""),
        "DATADOG_DASHBOARD": str(cfg.get("datadog_dashboard") or ""),
        "DEFAULT_RPS": str(cfg.get("rps") or "50"),
        "DEFAULT_DURATION": str(cfg.get("duration") or "5m"),
        "DEMO_REPLICAS": str(cfg.get("demo_replicas") or "1"),
    }
    if region:
        values["REGION"] = region
        values["LOG_REGION"] = log_region
        values["LOGS_DIR"] = logs_dir(cfg, region)
    return values


def emit_export_env(name: str, region: Optional[str] = None) -> str:
    lines = []
    for key, value in env_map(name, region).items():
        lines.append(f"{key}={shlex.quote(str(value))}")
    return "\n".join(lines) + "\n"


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Holiday-test service catalog")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List service ids")

    p_resolve = sub.add_parser("resolve", help="Resolve alias to catalog id")
    p_resolve.add_argument("name")

    p_get = sub.add_parser("get", help="Print one field")
    p_get.add_argument("name")
    p_get.add_argument("field")
    p_get.add_argument("--region")

    p_json = sub.add_parser("json", help="Dump resolved service as JSON")
    p_json.add_argument("name")
    p_json.add_argument("--region")

    p_env = sub.add_parser("export-env", help="Print KEY=value lines for eval")
    p_env.add_argument("name")
    p_env.add_argument("--region")

    p_logs = sub.add_parser("logs-dir", help="Print local logs directory name")
    p_logs.add_argument("name")
    p_logs.add_argument("region")

    args = parser.parse_args()
    try:
        if args.cmd == "list":
            catalog = load_catalog()
            for sid in list_ids(catalog):
                cfg = get_service(sid, catalog)
                aliases = ",".join(cfg.get("aliases") or [])
                extra = f"  aliases={aliases}" if aliases else ""
                print(f"{sid}\t{cfg.get('display_name', sid)}\t{cfg.get('payload_mode')}\tns={cfg.get('namespace')}{extra}")
            return 0
        if args.cmd == "resolve":
            print(resolve_id(args.name))
            return 0
        if args.cmd == "get":
            cfg = get_service(args.name)
            field = args.field
            if field == "logs_dir":
                if not args.region:
                    raise CatalogError("--region is required for logs_dir")
                print(logs_dir(cfg, args.region))
                return 0
            if field == "log_region":
                if not args.region:
                    raise CatalogError("--region is required for log_region")
                print(log_region_for(cfg, args.region))
                return 0
            if field == "s3_bucket":
                print(s3_results_uri(cfg, args.region))
                return 0
            if field == "s3_logs_uri":
                if not args.region:
                    raise CatalogError("--region is required for s3_logs_uri")
                print(s3_logs_uri(cfg, args.region))
                return 0
            value = cfg.get(field)
            if value is None:
                raise CatalogError(f"Unknown field '{field}'")
            if isinstance(value, list):
                print(",".join(str(v) for v in value))
            elif isinstance(value, bool):
                print("true" if value else "false")
            else:
                print(value)
            return 0
        if args.cmd == "json":
            cfg = get_service(args.name)
            if args.region:
                cfg["log_region"] = log_region_for(cfg, args.region)
                cfg["logs_dir"] = logs_dir(cfg, args.region)
                cfg["s3_results_uri"] = s3_results_uri(cfg, args.region)
                cfg["s3_logs_uri"] = s3_logs_uri(cfg, args.region)
            print(json.dumps(cfg, indent=2))
            return 0
        if args.cmd == "export-env":
            sys.stdout.write(emit_export_env(args.name, args.region))
            return 0
        if args.cmd == "logs-dir":
            print(logs_dir(get_service(args.name), args.region))
            return 0
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
