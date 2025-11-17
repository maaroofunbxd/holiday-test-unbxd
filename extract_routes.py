#!/usr/bin/env python3
"""
Extract all routes from a FastAPI application using FastAPI's built-in introspection.

Usage:
    # Run from holiday-test-unbxd directory:
    python3 extract_routes.py --app-path ../reranker

    # Or from anywhere:
    python3 extract_routes.py --app-path /path/to/reranker --output reranker_routes.json
"""

import sys
import json
import argparse
from pathlib import Path


def extract_routes_from_app(app_path):
    """Extract all routes from the FastAPI app."""
    # Add app path to sys.path so we can import it
    app_path = Path(app_path).resolve()
    if str(app_path) not in sys.path:
        sys.path.insert(0, str(app_path))
    
    try:
        # Import the FastAPI app
        from asgi import asgi as app
    except ImportError as e:
        print(f"❌ Error: Could not import FastAPI app from {app_path}")
        print(f"   Make sure the path is correct and contains asgi.py with 'asgi' app")
        print(f"   Error: {e}")
        sys.exit(1)
    
    routes = []
    
    for route in app.routes:
        # Skip routes without path
        if not hasattr(route, 'path'):
            continue
        
        route_info = {
            'path': route.path,
            'methods': sorted(list(route.methods)) if hasattr(route, 'methods') else [],
            'name': route.name if hasattr(route, 'name') else None,
        }
        
        routes.append(route_info)
    
    return routes


def routes_to_service_config(routes, service_name='reranker'):
    """Convert routes to service_endpoints.json format."""
    import re
    
    service_config = {
        'endpoints': {},
        'default_endpoint': None
    }
    
    for route in routes:
        path = route['path']
        methods = route['methods']
        
        # Skip health/monitor endpoints
        if path in ['/monitor', '/health', '/metrics', '/']:
            continue
        
        # Skip OPTIONS
        methods = [m for m in methods if m != 'OPTIONS']
        if not methods:
            continue
        
        # Get primary method
        primary_method = 'POST' if 'POST' in methods else methods[0]
        
        # Generate endpoint name from path
        # Extract version
        version = None
        if '/v1.0/' in path:
            version = 'v1.0'
        elif '/v2.0/' in path:
            version = 'v2.0'
        elif '/v3.0/' in path:
            version = 'v3.0'
        
        # Get endpoint name (last part of path, excluding parameters)
        clean_path = re.sub(r'/sites/\{[^}]+\}/', '/', path)
        clean_path = re.sub(r'/verticals/\{[^}]+\}/', '/', clean_path)
        clean_path = re.sub(r'/datasets/\{[^}]+\}/', '/', clean_path)
        
        parts = [p for p in clean_path.split('/') if p and not p.startswith('{')]
        endpoint_name = '_'.join(parts) if parts else 'root'
        
        # Clean up common prefixes
        endpoint_name = endpoint_name.replace('v1.0_', '').replace('v2.0_', '').replace('v3.0_', '')
        
        # Add version suffix for non-v1
        if version == 'v2.0':
            endpoint_name = f"{endpoint_name}_v2"
        elif version == 'v3.0':
            endpoint_name = f"{endpoint_name}_v3"
        
        # Create endpoint config
        endpoint_config = {
            'path': path,
            'method': primary_method,
        }
        
        if version:
            endpoint_config['version'] = version
        
        service_config['endpoints'][endpoint_name] = endpoint_config
    
    # Set default endpoint
    if 'recommend_v2' in service_config['endpoints']:
        service_config['default_endpoint'] = 'recommend_v2'
    elif 'recommend' in service_config['endpoints']:
        service_config['default_endpoint'] = 'recommend'
    
    return service_config


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extract routes from FastAPI app'
    )
    parser.add_argument(
        '--app-path',
        default='../reranker',
        help='Path to the FastAPI application directory (default: ../reranker)'
    )
    parser.add_argument(
        '--output', '-o',
        default='reranker_routes.json',
        help='Output JSON file (default: reranker_routes.json)'
    )
    parser.add_argument(
        '--service',
        default='reranker',
        help='Service name (default: reranker)'
    )
    parser.add_argument(
        '--format',
        choices=['simple', 'config'],
        default='config',
        help='Output format: simple (just routes) or config (service_endpoints.json format)'
    )
    
    args = parser.parse_args()
    
    print(f"🔍 Extracting routes from FastAPI app at {args.app_path}...")
    
    # Extract routes
    routes = extract_routes_from_app(args.app_path)
    
    print(f"\n📋 Found {len(routes)} routes:")
    for route in routes:
        methods_str = ','.join(route['methods']) if route['methods'] else 'N/A'
        print(f"  [{methods_str:20}] {route['path']}")
    
    # Convert to desired format
    if args.format == 'simple':
        output_data = routes
    else:
        output_data = {args.service: routes_to_service_config(routes, args.service)}
        print(f"\n📝 Generated config with {len(output_data[args.service]['endpoints'])} endpoints")
    
    # Write to file
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Routes written to {output_path}")
    print(f"\n💡 To update service_endpoints.json:")
    print(f"   1. Review {output_path}")
    print(f"   2. Copy the '{args.service}' section to service_endpoints.json")
