#!/usr/bin/env python3
"""
Replay a single request from JSONL file or JSON data.

Uses only Python standard library (urllib) - no external dependencies needed.

Usage:
    # Replay a specific line from JSONL file
    python3 replay_request.py -i requests.jsonl -n 5
    
    # Replay from JSON string
    python3 replay_request.py -j '{"type":"post","path":"/v2.0/sites/test/recommend","payload":{"platform":"netcore"}}'
    
    # Show curl command ONLY (for copy-paste debugging)
    python3 replay_request.py -i requests.jsonl -n 5 --curl-only --base-url http://localhost:8080
    
    # Execute the request (default uses urllib)
    python3 replay_request.py -i requests.jsonl -n 5 --base-url http://localhost:8080
"""

import json
import sys
import argparse
from urllib.parse import urlparse, urlencode, parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def build_url(request_data, base_url=None):
    """Build URL from request data."""
    path = request_data.get("path", "")
    sitekey = request_data.get("sitekey", "")
    
    if base_url:
        base_url = base_url.rstrip('/')
        if path.startswith('/'):
            url = f"{base_url}{path}"
        else:
            url = f"{base_url}/{path}"
    elif path.startswith('http'):
        url = path
    elif path:
        url = f"http://localhost{path}"
    else:
        # Try to construct from sitekey and api
        api = request_data.get("api", "recommend_v2")
        if sitekey:
            if api == "rerank":
                url = f"http://localhost/v1.0/sites/{sitekey}/rerank"
            elif api == "recommend_v2":
                url = f"http://localhost/v2.0/sites/{sitekey}/recommend"
            else:
                url = f"http://localhost/v1.0/sites/{sitekey}/recommend"
        else:
            url = "http://localhost"
    
    return url


def build_xh_command(request_data, base_url=None):
    """Build xh command that can be copy-pasted and executed."""
    import shlex
    
    request_type = request_data.get("type", "post").lower()
    url = build_url(request_data, base_url)
    
    # xh uses ./xh (relative path)
    cmd_parts = ["./xh", request_type.upper()]
    
    # Add URL first (xh format: xh METHOD URL [headers] [body])
    if request_type == "get":
        query_string = request_data.get("query_string", "")
        if query_string:
            if query_string.startswith('?'):
                url += query_string
            else:
                url += '?' + query_string
    
    cmd_parts.append(url)
    
    # Add headers (xh format: Header:value - no space after colon)
    headers = request_data.get("headers", {})
    for key, value in headers.items():
        if key.lower() not in ['host', 'content-length']:
            # xh header format: Header:value (no space)
            header_str = f"{key}:{value}"
            cmd_parts.append(header_str)
    
    if request_type == "post":
        payload = request_data.get("payload", {})
        if payload:
            # Add Content-Type header if not present
            has_content_type = any(
                k.lower() == 'content-type' 
                for k in headers.keys()
            )
            if not has_content_type:
                cmd_parts.append("Content-Type:application/json")
            
            # xh can take JSON with --raw flag for complex JSON
            payload_json = json.dumps(payload)
            # Use --raw for JSON body
            cmd_parts.append("--raw")
            cmd_parts.append(shlex.quote(payload_json))
    
    return " ".join(cmd_parts)


def replay_request(request_data, base_url=None, show_xh=False, use_xh=False, xh_only=False):
    """Replay a request using urllib (standard library) or curl."""
    request_type = request_data.get("type", "post").lower()
    url = build_url(request_data, base_url)
    
    # Prepare headers
    headers = {}
    original_headers = request_data.get("headers", {})
    for key, value in original_headers.items():
        if key.lower() not in ['host', 'content-length']:
            headers[key] = value
    
    if request_type == "post":
        if "Content-Type" not in headers and "content-type" not in {k.lower() for k in headers.keys()}:
            headers["Content-Type"] = "application/json"
    
    # Show xh command if requested
    if xh_only:
        xh_cmd = build_xh_command(request_data, base_url)
        print("=" * 80)
        print("XH COMMAND (copy-paste to run manually):")
        print("=" * 80)
        print(xh_cmd)
        print("=" * 80)
        print("\n💡 Copy the command above and run it in your terminal")
        return None
    
    if show_xh or use_xh:
        xh_cmd = build_xh_command(request_data, base_url)
        print("xh command:")
        print(xh_cmd)
        print()
        
        if use_xh:
            # Execute xh via subprocess
            import subprocess
            import shlex
            try:
                # Parse the xh command properly
                cmd = shlex.split(xh_cmd)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                print(f"Status: {result.returncode}")
                if result.stdout:
                    print(f"\nResponse:")
                    print(result.stdout)
                if result.stderr:
                    print(f"\nError output:")
                    print(result.stderr)
                return result
            except FileNotFoundError:
                print("Error: xh not found at ./xh. Please check path or use --use-urllib", file=sys.stderr)
                return None
            except subprocess.TimeoutExpired:
                print("Error: Request timed out", file=sys.stderr)
                return None
    
    # Execute using urllib (standard library)
    try:
        if request_type == "get":
            query_string = request_data.get("query_string", "")
            if query_string:
                if query_string.startswith('?'):
                    query_string = query_string[1:]
                if query_string:
                    if '?' in url:
                        url += '&' + query_string
                    else:
                        url += '?' + query_string
            
            print(f"GET {url}")
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as response:
                status_code = response.getcode()
                response_headers = dict(response.headers)
                response_data = response.read().decode('utf-8')
                
                print(f"\nStatus: {status_code}")
                print(f"Headers: {response_headers}")
                
                # Try to parse JSON
                try:
                    response_json = json.loads(response_data)
                    print(f"\nResponse JSON:")
                    print(json.dumps(response_json, indent=2))
                except:
                    print(f"\nResponse Text:")
                    print(response_data[:500])
                
                return response
        else:  # POST
            payload = request_data.get("payload", {})
            print(f"POST {url}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            # Encode payload as JSON
            payload_bytes = json.dumps(payload).encode('utf-8')
            
            req = Request(url, data=payload_bytes, headers=headers, method='POST')
            with urlopen(req, timeout=30) as response:
                status_code = response.getcode()
                response_headers = dict(response.headers)
                response_data = response.read().decode('utf-8')
                
                print(f"\nStatus: {status_code}")
                print(f"Headers: {response_headers}")
                
                # Try to parse JSON
                try:
                    response_json = json.loads(response_data)
                    print(f"\nResponse JSON:")
                    print(json.dumps(response_json, indent=2))
                except:
                    print(f"\nResponse Text:")
                    print(response_data[:500])
                
                return response
        
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        try:
            error_body = e.read().decode('utf-8')
            print(f"Error body: {error_body[:500]}", file=sys.stderr)
        except:
            pass
        return None
    except URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Replay requests from JSONL or JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute using urllib (default, no dependencies)
  python3 replay_request.py -i requests.jsonl -n 5 --base-url http://localhost:8080
  
  # ONLY show xh command (don't execute) - for debugging
  python3 replay_request.py -i requests.jsonl -n 5 --xh-only --base-url http://localhost:8080
  
  # Show xh command AND execute with urllib
  python3 replay_request.py -i requests.jsonl -n 5 --show-xh --base-url http://localhost:8080
  
  # Execute using xh (requires xh at /home/ai-prod-ap-southeast-2-eks/mrf/xh)
  python3 replay_request.py -i requests.jsonl -n 5 --use-xh --base-url http://localhost:8080
  
  # Replay from JSON string
  python3 replay_request.py -j '{"type":"post","path":"/v2.0/sites/test/recommend","payload":{"platform":"netcore"}}' --base-url http://localhost:8080
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        help="Input JSONL file"
    )
    parser.add_argument(
        "-n", "--line-number",
        type=int,
        help="Line number in JSONL file (1-indexed)"
    )
    parser.add_argument(
        "-j", "--json",
        help="JSON request data as string"
    )
    parser.add_argument(
        "--base-url",
        help="Base URL (e.g., http://localhost:8080)"
    )
    parser.add_argument(
        "--show-xh",
        action="store_true",
        help="Show xh command before executing"
    )
    parser.add_argument(
        "--show-curl",
        action="store_true",
        dest="show_xh",
        help="[Deprecated] Alias for --show-xh"
    )
    parser.add_argument(
        "--xh-only",
        action="store_true",
        help="ONLY show xh command (don't execute) - for copy-paste debugging"
    )
    parser.add_argument(
        "--curl-only",
        action="store_true",
        dest="xh_only",
        help="[Deprecated] Alias for --xh-only"
    )
    parser.add_argument(
        "--use-xh",
        action="store_true",
        help="Execute using xh (requires ./xh in current directory)"
    )
    parser.add_argument(
        "--use-curl",
        action="store_true",
        dest="use_xh",
        help="[Deprecated] Alias for --use-xh"
    )
    parser.add_argument(
        "--use-urllib",
        action="store_true",
        default=True,
        help="Execute using Python urllib (default, no dependencies)"
    )
    
    args = parser.parse_args()
    
    # Get request data
    request_data = None
    
    if args.json:
        try:
            request_data = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.input and args.line_number:
        try:
            with open(args.input, 'r') as f:
                lines = f.readlines()
                if args.line_number < 1 or args.line_number > len(lines):
                    print(f"Error: Line number {args.line_number} out of range (1-{len(lines)})", file=sys.stderr)
                    sys.exit(1)
                
                line = lines[args.line_number - 1].strip()
                if not line:
                    print(f"Error: Line {args.line_number} is empty", file=sys.stderr)
                    sys.exit(1)
                
                request_data = json.loads(line)
        except FileNotFoundError:
            print(f"Error: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSONL line {args.line_number}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
    
    if not request_data:
        print("Error: No request data found", file=sys.stderr)
        sys.exit(1)
    
    # Show request info
    print("Request:")
    print(json.dumps(request_data, indent=2))
    print()
    
    # Execute request
    replay_request(
        request_data, 
        args.base_url, 
        show_xh=getattr(args, 'show_xh', False) or getattr(args, 'show_curl', False),
        use_xh=getattr(args, 'use_xh', False) or getattr(args, 'use_curl', False),
        xh_only=getattr(args, 'xh_only', False) or getattr(args, 'curl_only', False)
    )


if __name__ == "__main__":
    main()
