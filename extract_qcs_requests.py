#!/usr/bin/env python3
# python3 extract_qcs_requests.py -i qcs_logs.txt -o qcs_requests.jsonl
import json
import re
import argparse
from urllib.parse import urlparse
from service_endpoints import get_qcs_path


def extract_qcs_request(line):
    """Extract QCS GET request data from log lines."""
    # Pattern to match QCS GET requests
    # Example: 10.0.99.210:53512 - "GET /v2/sites/boscovs-com811221579175852/category?category_level=ALL&deployment=live&model=statistical&query=Kitchen+Mats+Rugs HTTP/1.1" 200
    get_pattern = re.compile(r'\"GET\s+(/v2/sites/[^\s]+)\s+HTTP/[\d\.]+\"\s+(\d+)')
    match = get_pattern.search(line)
    
    if not match:
        return None
    
    full_path = match.group(1)
    status_code = match.group(2)
    
    # Parse the URL to extract path and query parameters
    parsed = urlparse(full_path)
    path_parts = parsed.path.split('/')
    
    # Extract sitekey from path: /v2/sites/{sitekey}/category
    sitekey = None
    if len(path_parts) >= 4 and path_parts[1] == 'v2' and path_parts[2] == 'sites':
        sitekey = path_parts[3]
    
    # Extract endpoint (e.g., "category")
    endpoint = path_parts[-1] if len(path_parts) > 4 else None
    
    # Extract raw query string (keep as-is for k6 to use directly)
    query_string = parsed.query if parsed.query else ""
    if query_string and not query_string.startswith('?'):
        query_string = '?' + query_string
    
    entry = {
        "type": "get",
        "sitekey": sitekey,
        "endpoint": endpoint,
        "path": parsed.path,
        "query_string": query_string,  # Raw query string to append to URL
        "status_code": int(status_code)
    }
    
    return entry


def extract_qcs_requests(input_file, output_file, include_errors=False):
    """Extract QCS GET requests from log files."""
    extracted_count = 0
    error_count = 0
    
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            # Look for GET request lines
            if '"GET /v2/sites/' in line:
                entry = extract_qcs_request(line)
                
                if entry:
                    # Optionally filter by status code
                    if not include_errors and entry["status_code"] >= 400:
                        error_count += 1
                        continue
                    
                    # Write entry as JSON
                    json.dump(entry, outfile)
                    outfile.write("\n")
                    extracted_count += 1
    
    return extracted_count, error_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract QCS GET requests from log files into JSONL format"
    )
    parser.add_argument(
        "-i", "--input",
        default="qcs_logs.txt",
        help="Input file containing raw QCS logs (default: qcs_logs.txt)"
    )
    parser.add_argument(
        "-o", "--output",
        default="qcs_requests.jsonl",
        help="Output JSONL file (default: qcs_requests.jsonl)"
    )
    parser.add_argument(
        "--include-errors", action="store_true",
        help="Include requests with error status codes (4xx, 5xx)"
    )

    args = parser.parse_args()

    extracted_count, error_count = extract_qcs_requests(
        input_file=args.input,
        output_file=args.output,
        include_errors=args.include_errors
    )

    print(f"✅ Extracted {extracted_count} QCS requests written to {args.output}")
    if error_count > 0:
        print(f"ℹ️  Skipped {error_count} requests with error status codes (use --include-errors to include them)")

