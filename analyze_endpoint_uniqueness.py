#!/usr/bin/env python3
"""
Analyze service endpoints to find unique identifiers for each API.
This helps in automatically identifying which endpoint a request is for.

Usage:
    python3 analyze_endpoint_uniqueness.py
    python3 analyze_endpoint_uniqueness.py --service reranker
"""

import re
import argparse
from collections import defaultdict
from service_endpoints import get_endpoints


def extract_path_features(path):
    """Extract features from a path that could be used as identifiers."""
    features = {}
    
    # Remove parameter placeholders for pattern matching
    clean_path = re.sub(r'\{[^}]+\}', '{param}', path)
    
    # Path segments (excluding parameters)
    segments = [seg for seg in path.split('/') if seg and not seg.startswith('{')]
    features['segments'] = segments
    features['segment_count'] = len(segments)
    
    # Unique keywords in path
    features['keywords'] = set(segments)
    
    # Last segment (often most identifying)
    features['last_segment'] = segments[-1] if segments else None
    
    # Path pattern
    features['pattern'] = clean_path
    
    # Check for specific path structures
    if '/sites/' in path:
        features['entity_type'] = 'sites'
    elif '/verticals/' in path:
        features['entity_type'] = 'verticals'
    elif '/datasets/' in path:
        features['entity_type'] = 'datasets'
    
    # Extract version
    version_match = re.search(r'/v(\d+\.\d+)/', path)
    if version_match:
        features['version'] = version_match.group(1)
    
    # Check for nested resources
    if path.count('/') > 4:  # More than just /v1.0/entity/{id}/resource
        features['nested'] = True
        # Extract the nested part
        parts = path.split('/')
        if len(parts) > 5:
            features['nested_resource'] = '/'.join(parts[5:])
    
    return features


def find_unique_identifiers(endpoints_by_method):
    """
    Find unique identifiers for each endpoint within the same HTTP method group.
    
    Returns a dict mapping endpoint names to their unique identifiers.
    """
    unique_ids = {}
    
    for method, endpoints in endpoints_by_method.items():
        print(f"\n{'='*60}")
        print(f"Analyzing {method} endpoints")
        print(f"{'='*60}")
        
        if not endpoints:
            continue
        
        # Extract features for all endpoints
        endpoint_features = {}
        for name, config in endpoints.items():
            path = config['path']
            endpoint_features[name] = extract_path_features(path)
        
        # Find unique identifiers for each endpoint
        for name, features in endpoint_features.items():
            identifiers = []
            
            # Check if last segment is unique
            last_segments = [f['last_segment'] for f in endpoint_features.values()]
            if features['last_segment'] and last_segments.count(features['last_segment']) == 1:
                identifiers.append({
                    'type': 'last_segment',
                    'value': features['last_segment'],
                    'description': f"Last path segment is '{features['last_segment']}'"
                })
            
            # Check for unique keywords
            unique_keywords = features['keywords']
            for other_name, other_features in endpoint_features.items():
                if other_name != name:
                    unique_keywords = unique_keywords - other_features['keywords']
            
            if unique_keywords:
                identifiers.append({
                    'type': 'unique_keywords',
                    'value': list(unique_keywords),
                    'description': f"Contains unique keyword(s): {', '.join(unique_keywords)}"
                })
            
            # Check if full pattern is unique
            patterns = [f['pattern'] for f in endpoint_features.values()]
            if patterns.count(features['pattern']) == 1:
                identifiers.append({
                    'type': 'pattern',
                    'value': features['pattern'],
                    'description': f"Unique path pattern"
                })
            
            # Check for nested resource uniqueness
            if 'nested_resource' in features:
                nested_resources = [f.get('nested_resource') for f in endpoint_features.values()]
                if nested_resources.count(features['nested_resource']) == 1:
                    identifiers.append({
                        'type': 'nested_resource',
                        'value': features['nested_resource'],
                        'description': f"Unique nested resource: {features['nested_resource']}"
                    })
            
            # Check entity type + last segment combination
            entity_key = f"{features.get('entity_type', 'none')}:{features['last_segment']}"
            entity_keys = [f"{f.get('entity_type', 'none')}:{f['last_segment']}" 
                          for f in endpoint_features.values()]
            if entity_keys.count(entity_key) == 1:
                identifiers.append({
                    'type': 'entity_segment',
                    'value': entity_key,
                    'description': f"Unique entity+segment: {entity_key}"
                })
            
            unique_ids[name] = {
                'method': method,
                'path': config['path'],
                'identifiers': identifiers,
                'features': features
            }
            
            # Print results
            print(f"\n{name}:")
            print(f"  Path: {config['path']}")
            if identifiers:
                print(f"  Unique identifiers:")
                for ident in identifiers:
                    print(f"    - {ident['description']}")
            else:
                print(f"  ⚠️  No simple unique identifier found!")
                print(f"     Use full path pattern: {features['pattern']}")
    
    return unique_ids


def generate_detection_code(service_name, unique_ids):
    """Generate Python code to detect endpoints from requests."""
    
    print(f"\n\n{'='*60}")
    print(f"Generated Detection Code for {service_name}")
    print(f"{'='*60}\n")
    
    code = f'''def detect_{service_name}_endpoint(path: str, method: str) -> str:
    """
    Detect {service_name} endpoint from request path and method.
    
    Args:
        path: Request path (e.g., /v1.0/sites/mysite/rerank)
        method: HTTP method (GET, POST, PUT, DELETE)
    
    Returns:
        Endpoint name or None if not recognized
    """
    # Normalize method
    method = method.upper()
    
'''
    
    # Group by method
    by_method = defaultdict(list)
    for name, info in unique_ids.items():
        by_method[info['method']].append((name, info))
    
    # Generate detection logic for each method
    for method in sorted(by_method.keys()):
        code += f"    if method == '{method}':\n"
        
        for name, info in by_method[method]:
            identifiers = info['identifiers']
            
            if not identifiers:
                # Use full path pattern
                pattern = info['features']['pattern']
                code += f"        # {name}\n"
                code += f"        if path_matches_pattern(path, '{pattern}'):\n"
                code += f"            return '{name}'\n"
                continue
            
            # Use the most specific identifier
            best_id = identifiers[0]  # First one is usually most specific
            
            if best_id['type'] == 'last_segment':
                segment = best_id['value']
                code += f"        # {name}\n"
                code += f"        if path.endswith('/{segment}'):\n"
                code += f"            return '{name}'\n"
            
            elif best_id['type'] == 'unique_keywords':
                keywords = best_id['value']
                conditions = [f"'/{kw}/' in path" for kw in keywords]
                code += f"        # {name}\n"
                code += f"        if {' or '.join(conditions)}:\n"
                code += f"            return '{name}'\n"
            
            elif best_id['type'] == 'nested_resource':
                resource = best_id['value']
                code += f"        # {name}\n"
                code += f"        if '{resource}' in path:\n"
                code += f"            return '{name}'\n"
            
            elif best_id['type'] == 'pattern':
                pattern = best_id['value']
                code += f"        # {name}\n"
                code += f"        if path_matches_pattern(path, '{pattern}'):\n"
                code += f"            return '{name}'\n"
    
    code += '''    
    return None


def path_matches_pattern(path: str, pattern: str) -> bool:
    """Check if path matches pattern (with {param} placeholders)."""
    # Convert pattern to regex
    regex_pattern = pattern.replace('{param}', '[^/]+')
    regex_pattern = '^' + regex_pattern + '$'
    return bool(re.match(regex_pattern, path))
'''
    
    print(code)
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze endpoint uniqueness and generate detection code'
    )
    parser.add_argument(
        '--service',
        default='reranker',
        help='Service to analyze (default: reranker)'
    )
    
    args = parser.parse_args()
    
    # Load endpoints
    endpoints_manager = get_endpoints()
    all_endpoints = endpoints_manager.get_all_endpoints(args.service)
    
    if not all_endpoints:
        print(f"❌ No endpoints found for service: {args.service}")
        exit(1)
    
    print(f"🔍 Analyzing {len(all_endpoints)} endpoints for {args.service}...")
    
    # Group by method
    by_method = defaultdict(dict)
    for name, config in all_endpoints.items():
        method = config['method']
        by_method[method][name] = config
    
    # Find unique identifiers
    unique_ids = find_unique_identifiers(by_method)
    
    # Generate detection code
    detection_code = generate_detection_code(args.service, unique_ids)
    
    # Save to file
    output_file = f'{args.service}_endpoint_detector.py'
    with open(output_file, 'w') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write(f'"""\nAuto-generated endpoint detector for {args.service} service.\n"""\n\n')
        f.write('import re\n\n')
        f.write(detection_code)
    
    print(f"\n✅ Detection code saved to {output_file}")
    print(f"\n💡 Usage example:")
    print(f"    from {args.service}_endpoint_detector import detect_{args.service}_endpoint")
    print(f"    endpoint = detect_{args.service}_endpoint('/v1.0/sites/mysite/rerank', 'POST')")
    print(f"    # Returns: 'rerank'")

