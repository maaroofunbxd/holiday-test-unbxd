#!/usr/bin/env python3
"""
Extract sitekeys and platform/algo information from reranker kubectl logs.

Usage:
    kubectl logs deploy/reranker-demo -nsearch | python3 extract_reranker_sites.py
    python3 extract_reranker_sites.py -i reranker_logs.txt
    python3 extract_reranker_sites.py -i reranker_logs.txt --summary
"""

import json
import re
import sys
import argparse
import ast
from collections import defaultdict
from typing import Optional, Dict, Any


def extract_from_go_log(line: str, include_full_data=False) -> Optional[Dict[str, Any]]:
    """Extract request data from Go service logs (with 'received request')."""
    # Pattern to match JSON block at end of line
    json_pattern = re.compile(r'(\{.*\})\s*$')
    match = json_pattern.search(line)
    
    if not match:
        return None
    
    try:
        data = json.loads(match.group(1))
        
        # Extract relevant fields
        sitekey = data.get("sitekey")
        platform = data.get("platform")
        payload = data.get("payload", {})
        
        if not sitekey:
            return None
        
        # Extract algo and algoVersion from payload
        algo = payload.get("algo")
        algo_version = payload.get("algoVersion")
        api = data.get("api")
        
        result = {
            "type": "post",  # Go logs with "received request" always have payload (POST)
            "sitekey": sitekey,
            "platform": platform,
            "algo": algo,
            "algo_version": algo_version,
            "api": api
        }
        
        # Include full request data if requested
        if include_full_data:
            result["full_data"] = data
            result["payload"] = payload
            result["headers"] = data.get("headers", {})
            result["x-request-id"] = data.get("x-request-id")
            result["path"] = data.get("path")
        
        return result
    except json.JSONDecodeError:
        return None


def extract_from_python_log(line: str, include_full_data=False) -> Optional[Dict[str, Any]]:
    """Extract request data from Python service logs (with 'Recieved' and 'with headers')."""
    line_strip = line.strip()
    
    # Find the key markers in the log line
    recieved_match = re.search(r"Recieved\s+", line_strip, re.IGNORECASE)
    if not recieved_match:
        return None
    
    with_headers_pos = line_strip.find(" with headers:")
    for_sitekey_pos = line_strip.find(" for sitekey:")
    
    if with_headers_pos == -1 or for_sitekey_pos == -1:
        return None
    
    # Extract the substrings
    payload_start = recieved_match.end()
    payload_str = line_strip[payload_start:with_headers_pos].strip()
    
    headers_start = with_headers_pos + len(" with headers:")
    headers_str = line_strip[headers_start:for_sitekey_pos].strip()
    
    sitekey_start = for_sitekey_pos + len(" for sitekey:")
    sitekey = line_strip[sitekey_start:].strip()
    
    if not sitekey:
        return None
    
    # Parse payload if it's a dict
    platform = None
    algo = None
    algo_version = None
    api = None
    payload_json = None
    headers_json = None
    
    # Determine request type and parse payload
    request_type = None
    if payload_str.startswith('{'):
        # POST request - payload is a dict
        request_type = "post"
        try:
            payload_json = ast.literal_eval(payload_str)
            platform = payload_json.get("platform")
            algo = payload_json.get("algo")
            algo_version = payload_json.get("algoVersion")
            
            # Infer API from payload content
            if payload_json.get("rankingContext") is not None:
                api = "rerank"
            elif payload_json.get("pids") is not None or payload_json.get("algo") is not None:
                api = "recommend_v2"
        except (ValueError, SyntaxError):
            payload_json = None
    else:
        # GET request - payload is a query string
        request_type = "get"
        payload_json = payload_str
    
    # Parse headers
    try:
        headers_json = ast.literal_eval(headers_str)
    except (ValueError, SyntaxError):
        headers_json = {}
    
    result = {
        "type": request_type,
        "sitekey": sitekey,
        "platform": platform,
        "algo": algo,
        "algo_version": algo_version,
        "api": api
    }
    
    # Include full request data if requested
    if include_full_data:
        result["payload"] = payload_json
        result["headers"] = headers_json
        result["payload_str"] = payload_str  # Keep original string format
        result["headers_str"] = headers_str  # Keep original string format
    
    return result


def extract_sites(input_file, show_summary=False, limit=None, filter_api=None, filter_platform=None, filter_sitekey=None, extract_requests=False, output_file=None, show_table=False):
    """Extract site information from log file or stdin."""
    sites_data = defaultdict(lambda: {
        "platforms": set(),
        "algos": set(),
        "algo_versions": set(),
        "apis": set(),
        "services": set(),  # Track which service (Python/Go) handled the request
        "count": 0
    })
    
    # Normalize filter values
    if filter_api:
        filter_api = filter_api.lower()
    if filter_platform:
        filter_platform = filter_platform.lower()
    if filter_sitekey:
        filter_sitekey = filter_sitekey.lower()
    
    # For extracting individual requests
    requests_list = []
    
    # Determine input source
    if input_file == "-" or input_file is None:
        infile = sys.stdin
    else:
        infile = open(input_file, "r")
    
    try:
        for line_num, line in enumerate(infile, 1):
            if limit and line_num > limit:
                break
            
            entry = None
            service_type = None
            line_lower = line.strip().lower()
            
            # Try Go log format first
            if "received request" in line_lower:
                entry = extract_from_go_log(line, include_full_data=extract_requests)
                service_type = "Go"
            # Then try Python log format
            elif "with headers" in line_lower and "recieved" in line_lower:
                entry = extract_from_python_log(line, include_full_data=extract_requests)
                service_type = "Python"
            
            if entry and entry.get("sitekey"):
                # Apply filters
                should_include = True
                
                if filter_api:
                    entry_api = entry.get("api", "").lower() if entry.get("api") else ""
                    if entry_api != filter_api:
                        should_include = False
                
                if filter_platform and should_include:
                    entry_platform = entry.get("platform", "").lower() if entry.get("platform") else ""
                    if entry_platform != filter_platform:
                        should_include = False
                
                if filter_sitekey and should_include:
                    entry_sitekey = entry.get("sitekey", "").lower()
                    if filter_sitekey not in entry_sitekey:
                        should_include = False
                
                if not should_include:
                    continue
                
                sitekey = entry["sitekey"]
                sites_data[sitekey]["count"] += 1
                
                if entry.get("platform"):
                    sites_data[sitekey]["platforms"].add(entry["platform"])
                if entry.get("algo"):
                    sites_data[sitekey]["algos"].add(entry["algo"])
                if entry.get("algo_version"):
                    sites_data[sitekey]["algo_versions"].add(entry["algo_version"])
                if entry.get("api"):
                    sites_data[sitekey]["apis"].add(entry["api"])
                if service_type:
                    sites_data[sitekey]["services"].add(service_type)
                
                # Store individual request if extracting requests
                if extract_requests:
                    request_entry = {
                        "type": entry.get("type"),  # "get" or "post"
                        "sitekey": sitekey,
                        "api": entry.get("api"),
                        "platform": entry.get("platform"),
                        "algo": entry.get("algo"),
                        "algo_version": entry.get("algo_version"),
                        "service": service_type,
                        "line_number": line_num
                    }
                    
                    # Add full request data if available
                    if "payload" in entry:
                        request_entry["payload"] = entry["payload"]
                    if "headers" in entry:
                        request_entry["headers"] = entry["headers"]
                    if "path" in entry:
                        request_entry["path"] = entry["path"]
                    if "x-request-id" in entry:
                        request_entry["x-request-id"] = entry["x-request-id"]
                    if "full_data" in entry:
                        request_entry["full_data"] = entry["full_data"]
                    if "payload_str" in entry:
                        request_entry["payload_str"] = entry["payload_str"]
                    if "headers_str" in entry:
                        request_entry["headers_str"] = entry["headers_str"]
                    # For GET requests, add query_string if available
                    if entry.get("type") == "get" and "payload_str" in entry:
                        request_entry["query_string"] = entry["payload_str"]
                    
                    requests_list.append(request_entry)
    
    finally:
        if input_file != "-" and input_file is not None:
            infile.close()
    
    # Convert sets to sorted lists for display
    sites_summary = []
    for sitekey, data in sites_data.items():
        sites_summary.append({
            "sitekey": sitekey,
            "platforms": sorted(data["platforms"]) or ["N/A"],
            "algos": sorted(data["algos"]) or ["N/A"],
            "algo_versions": sorted(data["algo_versions"]) or ["N/A"],
            "apis": sorted(data["apis"]) or ["N/A"],
            "services": sorted(data["services"]) or ["Unknown"],
            "count": data["count"]
        })
    
    # Sort by count (descending)
    sites_summary.sort(key=lambda x: x["count"], reverse=True)
    
    # If extracting individual requests, write them to file
    if extract_requests and output_file:
        with open(output_file, 'w') as f:
            for req in requests_list:
                json.dump(req, f)
                f.write('\n')
    
    # Show output based on mode
    if extract_requests:
        # Print individual requests as JSON (one per line)
        if output_file:
            # Already written to file, just show summary
            print(f"\n✅ Extracted {len(requests_list)} requests to {output_file}")
        else:
            # Print requests as JSON, one per line
            for req in requests_list:
                print(json.dumps(req))
    elif show_table:
        # Show summary table
        print_summary(sites_summary, filter_api, filter_platform, filter_sitekey)
    elif show_summary:
        # Show detailed view (legacy, same as default)
        print_detailed(sites_summary, filter_api, filter_platform, filter_sitekey)
    else:
        # Default: detailed view
        print_detailed(sites_summary, filter_api, filter_platform, filter_sitekey)
    
    if extract_requests:
        return requests_list
    return sites_summary




def print_summary(sites_summary, filter_api=None, filter_platform=None, filter_sitekey=None):
    """Print a summary table of sites."""
    print("\n" + "=" * 120)
    print("RERANKER SITES SUMMARY")
    if filter_api:
        print(f"Filter: API = {filter_api}")
    if filter_platform:
        print(f"Filter: Platform = {filter_platform}")
    if filter_sitekey:
        print(f"Filter: Sitekey = {filter_sitekey}")
    print("=" * 120)
    print(f"{'Sitekey':<50} {'Platform':<18} {'Algo':<12} {'API':<12} {'Service':<12} {'Count':<8}")
    print("-" * 120)
    
    for site in sites_summary:
        sitekey_short = site["sitekey"][:48] + ".." if len(site["sitekey"]) > 50 else site["sitekey"]
        platform = ", ".join(site["platforms"][:2]) + ("..." if len(site["platforms"]) > 2 else "")
        algo = ", ".join(site["algos"][:2]) + ("..." if len(site["algos"]) > 2 else "")
        api = ", ".join(site["apis"][:2]) + ("..." if len(site["apis"]) > 2 else "")
        services = ", ".join(site["services"])
        
        print(f"{sitekey_short:<50} {platform:<18} {algo:<12} {api:<12} {services:<12} {site['count']:<8}")
    
    print("-" * 100)
    print(f"Total unique sites: {len(sites_summary)}")
    print(f"Total requests: {sum(s['count'] for s in sites_summary)}")


def print_detailed(sites_summary, filter_api=None, filter_platform=None, filter_sitekey=None):
    """Print detailed information for each site."""
    print("\n" + "=" * 100)
    print("RERANKER SITES DETAILED VIEW")
    if filter_api:
        print(f"Filter: API = {filter_api}")
    if filter_platform:
        print(f"Filter: Platform = {filter_platform}")
    if filter_sitekey:
        print(f"Filter: Sitekey = {filter_sitekey}")
    print("=" * 100)
    
    for i, site in enumerate(sites_summary, 1):
        print(f"\n{i}. Sitekey: {site['sitekey']}")
        print(f"   Requests: {site['count']}")
        print(f"   Service(s): {', '.join(site['services'])}")
        print(f"   Platform(s): {', '.join(site['platforms'])}")
        print(f"   Algorithm(s): {', '.join(site['algos'])}")
        print(f"   Algo Version(s): {', '.join(site['algo_versions'])}")
        print(f"   API(s): {', '.join(site['apis'])}")
    
    print("\n" + "-" * 100)
    print(f"Total unique sites: {len(sites_summary)}")
    print(f"Total requests: {sum(s['count'] for s in sites_summary)}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract sitekeys and platform/algo information from reranker kubectl logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From kubectl logs (stdin)
  kubectl logs deploy/reranker-demo -nsearch | python3 extract_reranker_sites.py
  
  # From a log file
  python3 extract_reranker_sites.py -i reranker_logs.txt
  
  # Summary view
  python3 extract_reranker_sites.py -i reranker_logs.txt --summary
  
  # Filter by API endpoint
  python3 extract_reranker_sites.py -i reranker_logs.txt --api rerank
  
  # Filter by platform
  python3 extract_reranker_sites.py -i reranker_logs.txt --platform netcore
  
  # Filter by both API and platform
  python3 extract_reranker_sites.py -i reranker_logs.txt --api rerank --platform netcore
  
  # Filter by sitekey (partial match)
  python3 extract_reranker_sites.py -i reranker_logs.txt --sitekey tangs
  
  # Filter by sitekey, API, and platform
  python3 extract_reranker_sites.py -i reranker_logs.txt --sitekey tangs --api rerank --platform netcore
  
  # Extract individual requests (prints JSON, one per line)
  python3 extract_reranker_sites.py -i reranker_logs.txt --extract-requests --api rerank
  
  # Extract requests to JSONL file
  python3 extract_reranker_sites.py -i reranker_logs.txt --extract-requests --platform semantic_search -o semantic_requests.jsonl
  
  # Show summary table view
  python3 extract_reranker_sites.py -i reranker_logs.txt --table
  
  # Show summary table with filters
  python3 extract_reranker_sites.py -i reranker_logs.txt --table --api rerank --platform netcore
  
  # Limit number of lines to process
  python3 extract_reranker_sites.py -i reranker_logs.txt --limit 1000
        """
    )
    parser.add_argument(
        "-i", "--input",
        default="-",
        help="Input file (default: stdin, use '-' for explicit stdin)"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary table instead of detailed view"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of log lines to process"
    )
    parser.add_argument(
        "--api",
        help="Filter by API endpoint (e.g., rerank, recommend_v2, recommend)"
    )
    parser.add_argument(
        "--platform",
        help="Filter by platform (e.g., netcore, semantic_search, image_search, unbxd)"
    )
    parser.add_argument(
        "--sitekey",
        help="Filter by sitekey (partial match supported, case-insensitive)"
    )
    parser.add_argument(
        "--extract-requests",
        action="store_true",
        help="Extract individual requests with full data (payload, headers, etc.). Prints JSON, one request per line"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file for extracted requests (JSONL format). Only used with --extract-requests"
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Show summary table view (instead of detailed view)"
    )
    
    args = parser.parse_args()
    
    extract_sites(
        args.input, 
        show_summary=args.summary, 
        limit=args.limit,
        filter_api=args.api,
        filter_platform=args.platform,
        filter_sitekey=args.sitekey,
        extract_requests=args.extract_requests,
        output_file=args.output,
        show_table=args.table
    )


if __name__ == "__main__":
    main()
