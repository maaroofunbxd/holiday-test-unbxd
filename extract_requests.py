#!/usr/bin/env python3
# python3 extract_requests.py -i reranker_logs_go.txt -o requests_go.jsonl
import json
import re
import argparse
import ast
from urllib.parse import parse_qs


def debug_py(line):
    """Extract payload and headers from Python service logs."""
    line_strip = line.strip()
    
    # Find the key markers in the log line (may have log prefix like INFO:server:)
    # Match "Recieved" specifically
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
    
    # Determine if payload is dict format or query string format
    try:
        # Try parsing headers first (should always be dict format)
        headers_json = ast.literal_eval(headers_str)
        
        # Check if payload starts with '{' (dict format) or not (query string format)
        if payload_str.startswith('{'):
            # Parse as Python dictionary
            payload_json = ast.literal_eval(payload_str)
            entry = {
                "type": "with_headers",
                "sitekey": sitekey,
                "payload": payload_json,
                "headers": headers_json,
            }
        else:
            # Keep as raw query string - don't parse into payload
            entry = {
                "type": "with_headers",
                "sitekey": sitekey,
                "query_string": payload_str,  # Raw query string to append to URL
                "headers": headers_json,
            }
        return entry

    except (ValueError, SyntaxError) as e:
        print(f"⚠️  Skipping malformed 'with headers' data: {e}")
        print(f"   Line preview: {line[:100]}")
        return None


def debug_go(line, regex_pattern, require_payload=True, require_sitekey=True):
    """Extract request data from Go service logs."""
    json_pattern = re.compile(regex_pattern)
    match = json_pattern.search(line)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))

        # Optional filtering
        if require_payload and "payload" not in data:
            return None
        if require_sitekey and "sitekey" not in data:
            return None

        entry = {
            "x-request-id": data.get("x-request-id"),
            "api": data.get("api"),
            "sitekey": data.get("sitekey"),
            "platform": data.get("platform"),
            "payload": data.get("payload"),
        }
        return entry

    except json.JSONDecodeError:
        print("⚠️  Skipping malformed line:", line[:100])
        return None

def extract_requests(
    input_file,
    output_file,
    regex_pattern,
    require_payload=True,
    require_sitekey=True,
):
    """Extract and filter requests from log files."""
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            entry = None
            line_lower = line.strip().lower()
            
            # Only include specific log lines
            if "received request" in line_lower:
                entry = debug_go(
                    line, regex_pattern, require_payload, require_sitekey
                )
            elif "with headers" in line_lower and "recieved" in line_lower:
                entry = debug_py(line)

            if entry:
                # Write entry as JSON to preserve sitekey and metadata
                json.dump(entry, outfile)
                outfile.write("\n")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract JSON payloads from specific Kubernetes pod log lines into JSONL for k6"
    )
    parser.add_argument(
        "-i", "--input",
        default="pod_logs.txt",
        help="Input file containing raw pod logs (default: pod_logs.txt)"
    )
    parser.add_argument(
        "-o", "--output",
        default="requests.jsonl",
        help="Output JSONL file (default: requests.jsonl)"
    )
    parser.add_argument(
        "-r", "--regex",
        default=r'(\{.*\})\s*$',
        help=r"Regex pattern to capture JSON block (default: '(\{.*\})\s*$')"
    )
    parser.add_argument(
        "--no-payload", action="store_true",
        help="Do not require 'payload' field to exist"
    )
    parser.add_argument(
        "--no-sitekey", action="store_true",
        help="Do not require 'sitekey' field to exist"
    )

    args = parser.parse_args()

    extract_requests(
        input_file=args.input,
        output_file=args.output,
        regex_pattern=args.regex,
        require_payload=not args.no_payload,
        require_sitekey=not args.no_sitekey,
    )

    print(f"✅ Extracted requests written to {args.output}")
