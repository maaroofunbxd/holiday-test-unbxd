#!/usr/bin/env python3
"""
Analyze payload signatures to identify unique characteristics of each API endpoint.

This helps identify which endpoint a request belongs to based on:
- Payload field names (for POST/PUT)
- Query parameter names (for GET)
- Field combinations
- Required fields

Usage:
    python3 analyze_payload_signatures.py --logs reranker_logs.txt
    python3 analyze_payload_signatures.py --jsonl requests.jsonl
"""

import json
import argparse
from collections import defaultdict
from pathlib import Path
from service_endpoints import get_endpoints


def analyze_payload_fields(payloads):
    """
    Analyze a list of payloads to find common fields.
    
    Returns:
        - all_fields: set of all field names seen
        - field_frequency: how often each field appears
        - common_fields: fields that appear in >80% of requests
        - unique_fields: fields that ONLY appear in these payloads
    """
    if not payloads:
        return None
    
    all_fields = set()
    field_counts = defaultdict(int)
    
    for payload in payloads:
        if isinstance(payload, dict):
            fields = set(payload.keys())
            all_fields.update(fields)
            for field in fields:
                field_counts[field] += 1
    
    total = len(payloads)
    common_threshold = 0.8 * total
    
    common_fields = {field for field, count in field_counts.items() if count >= common_threshold}
    
    result = {
        'all_fields': all_fields,
        'field_frequency': dict(field_counts),
        'common_fields': common_fields,
        'total_samples': total
    }
    
    return result


def find_payload_signatures(requests_by_endpoint):
    """
    Find unique payload signatures for each endpoint.
    
    Args:
        requests_by_endpoint: dict mapping endpoint names to lists of requests
    
    Returns:
        dict mapping endpoint names to their signature characteristics
    """
    signatures = {}
    
    # First pass: analyze each endpoint
    endpoint_analyses = {}
    for endpoint_name, requests in requests_by_endpoint.items():
        payloads = []
        query_params = []
        
        for req in requests:
            if 'payload' in req and req['payload']:
                payloads.append(req['payload'])
            if 'query_string' in req and req['query_string']:
                # Parse query string into dict
                params = {}
                qs = req['query_string'].lstrip('?')
                for part in qs.split('&'):
                    if '=' in part:
                        key, val = part.split('=', 1)
                        params[key] = val
                query_params.append(params)
        
        analysis = {}
        
        if payloads:
            analysis['payload'] = analyze_payload_fields(payloads)
        
        if query_params:
            analysis['query_params'] = analyze_payload_fields(query_params)
        
        endpoint_analyses[endpoint_name] = analysis
    
    # Second pass: find unique identifiers
    for endpoint_name, analysis in endpoint_analyses.items():
        sig = {
            'endpoint': endpoint_name,
            'identifiers': []
        }
        
        # Check payload fields
        if 'payload' in analysis:
            my_fields = analysis['payload']['all_fields']
            my_common = analysis['payload']['common_fields']
            
            # Find fields unique to this endpoint
            unique_to_me = my_fields.copy()
            for other_name, other_analysis in endpoint_analyses.items():
                if other_name != endpoint_name and 'payload' in other_analysis:
                    other_fields = other_analysis['payload']['all_fields']
                    unique_to_me = unique_to_me - other_fields
            
            if unique_to_me:
                sig['identifiers'].append({
                    'type': 'unique_payload_fields',
                    'fields': list(unique_to_me),
                    'description': f"Unique payload fields: {', '.join(unique_to_me)}"
                })
            
            # Find combinations of common fields that are unique
            if my_common:
                unique_combo = True
                for other_name, other_analysis in endpoint_analyses.items():
                    if other_name != endpoint_name and 'payload' in other_analysis:
                        other_common = other_analysis['payload']['common_fields']
                        if my_common == other_common:
                            unique_combo = False
                            break
                
                if unique_combo and len(my_common) > 0:
                    sig['identifiers'].append({
                        'type': 'common_field_combination',
                        'fields': list(my_common),
                        'description': f"Common field combination: {', '.join(sorted(my_common))}"
                    })
            
            sig['payload_fields'] = {
                'all': list(my_fields),
                'common': list(my_common),
                'frequency': analysis['payload']['field_frequency']
            }
        
        # Check query parameters
        if 'query_params' in analysis:
            my_params = analysis['query_params']['all_fields']
            my_common_params = analysis['query_params']['common_fields']
            
            # Find params unique to this endpoint
            unique_params = my_params.copy()
            for other_name, other_analysis in endpoint_analyses.items():
                if other_name != endpoint_name and 'query_params' in other_analysis:
                    other_params = other_analysis['query_params']['all_fields']
                    unique_params = unique_params - other_params
            
            if unique_params:
                sig['identifiers'].append({
                    'type': 'unique_query_params',
                    'fields': list(unique_params),
                    'description': f"Unique query params: {', '.join(unique_params)}"
                })
            
            sig['query_params'] = {
                'all': list(my_params),
                'common': list(my_common_params),
                'frequency': analysis['query_params']['field_frequency']
            }
        
        signatures[endpoint_name] = sig
    
    return signatures


def load_requests_from_jsonl(jsonl_file):
    """Load requests from JSONL file and group by endpoint if available."""
    requests_by_endpoint = defaultdict(list)
    requests_unknown = []
    
    with open(jsonl_file, 'r') as f:
        for line in f:
            try:
                req = json.loads(line)
                
                # Try to determine endpoint from path or api field
                endpoint = req.get('endpoint') or req.get('api')
                
                if endpoint:
                    requests_by_endpoint[endpoint].append(req)
                else:
                    requests_unknown.append(req)
            except json.JSONDecodeError:
                continue
    
    return dict(requests_by_endpoint), requests_unknown


def generate_detector_code(signatures, service_name):
    """Generate Python code to detect endpoint from payload/query params."""
    
    code = f'''def detect_{service_name}_endpoint_from_data(payload=None, query_params=None, method=None):
    """
    Detect {service_name} endpoint from request data.
    
    Args:
        payload: Request payload (dict) for POST/PUT requests
        query_params: Query parameters (dict) for GET requests
        method: HTTP method (optional, helps narrow down)
    
    Returns:
        Endpoint name or None if not recognized
    """
    
    if payload:
        payload_fields = set(payload.keys())
        
'''
    
    # Group by whether they use payload or query params
    payload_endpoints = []
    query_endpoints = []
    
    for endpoint_name, sig in signatures.items():
        if 'payload_fields' in sig:
            payload_endpoints.append((endpoint_name, sig))
        if 'query_params' in sig:
            query_endpoints.append((endpoint_name, sig))
    
    # Generate payload detection
    if payload_endpoints:
        for endpoint_name, sig in payload_endpoints:
            identifiers = [i for i in sig['identifiers'] if 'payload' in i['type']]
            
            if identifiers:
                code += f"        # {endpoint_name}\n"
                
                for ident in identifiers:
                    if ident['type'] == 'unique_payload_fields':
                        unique_fields = ident['fields']
                        if len(unique_fields) == 1:
                            field = unique_fields[0]
                            code += f"        if '{field}' in payload_fields:\n"
                            code += f"            return '{endpoint_name}'\n"
                        else:
                            fields_check = ' or '.join([f"'{f}' in payload_fields" for f in unique_fields])
                            code += f"        if {fields_check}:\n"
                            code += f"            return '{endpoint_name}'\n"
                    
                    elif ident['type'] == 'common_field_combination':
                        common_fields = ident['fields']
                        if common_fields:
                            fields_check = ' and '.join([f"'{f}' in payload_fields" for f in common_fields])
                            code += f"        if {fields_check}:\n"
                            code += f"            return '{endpoint_name}'\n"
                code += "\n"
    
    # Generate query params detection
    if query_endpoints:
        code += "    if query_params:\n"
        code += "        param_keys = set(query_params.keys())\n\n"
        
        for endpoint_name, sig in query_endpoints:
            identifiers = [i for i in sig['identifiers'] if 'query' in i['type']]
            
            if identifiers:
                code += f"        # {endpoint_name}\n"
                
                for ident in identifiers:
                    if ident['type'] == 'unique_query_params':
                        unique_params = ident['fields']
                        if len(unique_params) == 1:
                            param = unique_params[0]
                            code += f"        if '{param}' in param_keys:\n"
                            code += f"            return '{endpoint_name}'\n"
                        else:
                            params_check = ' or '.join([f"'{p}' in param_keys" for p in unique_params])
                            code += f"        if {params_check}:\n"
                            code += f"            return '{endpoint_name}'\n"
                code += "\n"
    
    code += "    return None\n"
    
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze payload signatures to identify API endpoints'
    )
    parser.add_argument(
        '--jsonl',
        help='JSONL file with extracted requests'
    )
    parser.add_argument(
        '--service',
        default='reranker',
        help='Service name (default: reranker)'
    )
    
    args = parser.parse_args()
    
    if not args.jsonl:
        print("❌ Please provide --jsonl file with extracted requests")
        print("\nExample:")
        print("  python3 analyze_payload_signatures.py --jsonl requests.jsonl")
        exit(1)
    
    jsonl_path = Path(args.jsonl)
    if not jsonl_path.exists():
        print(f"❌ File not found: {args.jsonl}")
        exit(1)
    
    print(f"🔍 Analyzing requests from {args.jsonl}...")
    
    # Load requests
    requests_by_endpoint, unknown = load_requests_from_jsonl(args.jsonl)
    
    if not requests_by_endpoint:
        print("❌ No requests with endpoint information found!")
        print("   Make sure your JSONL has 'endpoint' or 'api' fields")
        exit(1)
    
    print(f"\n📊 Found requests for {len(requests_by_endpoint)} endpoints:")
    for endpoint, reqs in requests_by_endpoint.items():
        print(f"   - {endpoint}: {len(reqs)} requests")
    
    if unknown:
        print(f"\n⚠️  {len(unknown)} requests without endpoint info")
    
    # Analyze signatures
    print(f"\n🔬 Analyzing payload signatures...")
    signatures = find_payload_signatures(requests_by_endpoint)
    
    # Print results
    print(f"\n{'='*70}")
    print("PAYLOAD SIGNATURE ANALYSIS")
    print(f"{'='*70}\n")
    
    for endpoint_name, sig in signatures.items():
        print(f"\n{endpoint_name}:")
        print("-" * 50)
        
        if 'payload_fields' in sig:
            print(f"  Payload fields ({len(sig['payload_fields']['all'])} total):")
            print(f"    All: {', '.join(sorted(sig['payload_fields']['all']))}")
            if sig['payload_fields']['common']:
                print(f"    Common (>80%): {', '.join(sorted(sig['payload_fields']['common']))}")
        
        if 'query_params' in sig:
            print(f"  Query parameters ({len(sig['query_params']['all'])} total):")
            print(f"    All: {', '.join(sorted(sig['query_params']['all']))}")
            if sig['query_params']['common']:
                print(f"    Common (>80%): {', '.join(sorted(sig['query_params']['common']))}")
        
        if sig['identifiers']:
            print(f"\n  🎯 Unique identifiers:")
            for ident in sig['identifiers']:
                print(f"     ✓ {ident['description']}")
        else:
            print(f"\n  ⚠️  No unique identifier found!")
    
    # Generate detector code
    print(f"\n\n{'='*70}")
    print("GENERATED DETECTOR CODE")
    print(f"{'='*70}\n")
    
    detector_code = generate_detector_code(signatures, args.service)
    print(detector_code)
    
    # Save results
    output_file = f"{args.service}_payload_signatures.json"
    with open(output_file, 'w') as f:
        json.dump(signatures, f, indent=2)
    
    print(f"\n✅ Signatures saved to {output_file}")
    
    detector_file = f"{args.service}_payload_detector.py"
    with open(detector_file, 'w') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write(f'"""\nAuto-generated payload detector for {args.service}.\n"""\n\n')
        f.write(detector_code)
    
    print(f"✅ Detector saved to {detector_file}")

