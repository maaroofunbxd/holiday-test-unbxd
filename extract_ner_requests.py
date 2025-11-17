#!/usr/bin/env python3
# python3 extract_ner_requests.py -i ner_logs.txt -o ner_requests.jsonl
import json
import re
import argparse
from urllib.parse import urlparse
from service_endpoints import get_ner_path


def extract_ner_request(line):
    """Extract NER GET request data from Apache-style log lines."""
    # Pattern to match Apache/Nginx access log format
    # Example: 10.0.24.91 - - [07/Nov/2025:06:54:02 +0000] "GET /v1.0/sites/childrensplace-com702771523455856/tag?q=3055941 HTTP/1.1" 200 105 "-" "Go-http-client/1.1"
    log_pattern = re.compile(
        r'(\d+\.\d+\.\d+\.\d+)\s+-\s+-\s+\[([^\]]+)\]\s+"GET\s+([^\s]+)\s+HTTP/[\d\.]+"\s+(\d+)\s+(\d+)\s+"([^"]*)"\s+"([^"]*)"'
    )
    
    match = log_pattern.search(line)
    if not match:
        return None
    
    ip_address = match.group(1)
    timestamp = match.group(2)
    full_path = match.group(3)
    status_code = match.group(4)
    response_size = match.group(5)
    referer = match.group(6)
    user_agent = match.group(7)
    
    # Skip health check endpoints
    if full_path == '/monitor' or full_path.startswith('/health'):
        return None
    
    # Parse the URL to extract path and query parameters
    parsed = urlparse(full_path)
    path_parts = parsed.path.split('/')
    
    # Extract sitekey from path
    # Pattern 1: /v1.0/sites/{sitekey}/tag
    # Pattern 2: /api/v0/sites/{sitekey}/dimensions
    sitekey = None
    endpoint = None
    api_version = None
    
    if 'sites' in path_parts:
        sites_idx = path_parts.index('sites')
        if sites_idx + 1 < len(path_parts):
            sitekey = path_parts[sites_idx + 1]
        if sites_idx + 2 < len(path_parts):
            endpoint = path_parts[sites_idx + 2]
        
        # Get API version
        if len(path_parts) > 1:
            # Check for v1.0, v0, etc.
            for part in path_parts:
                if part.startswith('v') and any(c.isdigit() for c in part):
                    api_version = part
                    break
    
    # Extract raw query string (keep as-is for k6 to use directly)
    query_string = parsed.query if parsed.query else ""
    if query_string and not query_string.startswith('?'):
        query_string = '?' + query_string
    
    entry = {
        "type": "get",
        "sitekey": sitekey,
        "endpoint": endpoint,
        "api_version": api_version,
        "path": parsed.path,
        "query_string": query_string,  # Raw query string to append to URL
        "status_code": int(status_code),
        "response_size": int(response_size),
        "timestamp": timestamp,
        "ip_address": ip_address,
        "user_agent": user_agent
    }
    
    return entry


def extract_ner_requests(input_file, output_file, include_errors=False, skip_monitor=True):
    """Extract NER GET requests from log files."""
    extracted_count = 0
    error_count = 0
    skipped_monitor = 0
    
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            # Look for GET request lines
            if '"GET ' in line:
                # Skip monitor/health check endpoints if requested
                if skip_monitor and ('/monitor' in line or '/health' in line):
                    skipped_monitor += 1
                    continue
                
                entry = extract_ner_request(line)
                
                if entry:
                    # Optionally filter by status code
                    if not include_errors and entry["status_code"] >= 400:
                        error_count += 1
                        continue
                    
                    # Write entry as JSON
                    json.dump(entry, outfile)
                    outfile.write("\n")
                    extracted_count += 1
    
    return extracted_count, error_count, skipped_monitor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract NER GET requests from Apache-style log files into JSONL format"
    )
    parser.add_argument(
        "-i", "--input",
        default="ner_logs.txt",
        help="Input file containing raw NER logs (default: ner_logs.txt)"
    )
    parser.add_argument(
        "-o", "--output",
        default="ner_requests.jsonl",
        help="Output JSONL file (default: ner_requests.jsonl)"
    )
    parser.add_argument(
        "--include-errors", action="store_true",
        help="Include requests with error status codes (4xx, 5xx)"
    )
    parser.add_argument(
        "--include-monitor", action="store_true",
        help="Include /monitor and /health endpoint requests"
    )

    args = parser.parse_args()

    extracted_count, error_count, skipped_monitor = extract_ner_requests(
        input_file=args.input,
        output_file=args.output,
        include_errors=args.include_errors,
        skip_monitor=not args.include_monitor
    )

    print(f"✅ Extracted {extracted_count} NER requests written to {args.output}")
    if skipped_monitor > 0:
        print(f"ℹ️  Skipped {skipped_monitor} health check/monitor requests (use --include-monitor to include them)")
    if error_count > 0:
        print(f"ℹ️  Skipped {error_count} requests with error status codes (use --include-errors to include them)")

