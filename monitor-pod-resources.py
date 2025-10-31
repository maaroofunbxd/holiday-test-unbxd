#!/usr/bin/env python3
"""
Monitor Kubernetes pod resources showing current/limit as fractions
Usage: python3 monitor-pod-resources.py [--watch INTERVAL]
"""

import subprocess
import json
import sys
import time
import argparse


def parse_resource(value):
    """Convert k8s resource notation to comparable number"""
    if not value or value == "N/A":
        return None
    
    # Handle millicores (e.g., "100m" = 0.1 cores)
    if value.endswith('m'):
        return float(value[:-1]) / 1000
    
    # Handle memory units
    units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'K': 1000, 'M': 1000**2, 'G': 1000**3}
    for suffix, multiplier in units.items():
        if value.endswith(suffix):
            return float(value[:-len(suffix)]) * multiplier
    
    return float(value)


# Global cache for pod resource limits
POD_LIMITS_CACHE = {}


def get_pod_limits(pod_name):
    """Get pod resource limits, using cache if available"""
    # Check cache first
    if pod_name in POD_LIMITS_CACHE:
        return POD_LIMITS_CACHE[pod_name]
    
    # Fetch from API for new pods
    cmd = ["kubectl", "get", "pod", pod_name, "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return None
    
    pod_data = json.loads(result.stdout)
    container = pod_data['spec']['containers'][0]
    resources = container.get('resources', {})
    
    limits = {
        'cpu_request': resources.get('requests', {}).get('cpu', 'N/A'),
        'cpu_limit': resources.get('limits', {}).get('cpu', 'N/A'),
        'mem_request': resources.get('requests', {}).get('memory', 'N/A'),
        'mem_limit': resources.get('limits', {}).get('memory', 'N/A')
    }
    
    # Cache it
    POD_LIMITS_CACHE[pod_name] = limits
    print(f"[Cached new pod: {pod_name}]", file=sys.stderr)
    
    return limits


def get_pod_metrics():
    """Get current pod metrics and their limits"""
    # Get current usage
    cmd = ["kubectl", "top", "pods", "-l", "algo in (personalization,ranking)", "--no-headers"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running kubectl top: {result.stderr}")
        return []
    
    metrics = []
    current_pods = set()
    
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split()
        pod_name = parts[0]
        cpu_current = parts[1]
        mem_current = parts[2]
        
        current_pods.add(pod_name)
        
        # Get pod resource limits (from cache or API)
        limits = get_pod_limits(pod_name)
        if not limits:
            continue
        
        cpu_request = limits['cpu_request']
        cpu_limit = limits['cpu_limit']
        mem_request = limits['mem_request']
        mem_limit = limits['mem_limit']
        
        # Calculate fractions
        cpu_current_val = parse_resource(cpu_current)
        cpu_limit_val = parse_resource(cpu_limit)
        mem_current_val = parse_resource(mem_current)
        mem_limit_val = parse_resource(mem_limit)
        
        cpu_fraction = f"{cpu_current_val:.2f}/{cpu_limit_val:.2f}" if cpu_limit_val else f"{cpu_current}/N/A"
        mem_fraction_gb = f"{mem_current_val/(1024**3):.2f}/{mem_limit_val/(1024**3):.2f}Gi" if mem_limit_val else f"{mem_current}/N/A"
        
        metrics.append({
            'pod': pod_name,
            'cpu': cpu_fraction,
            'memory': mem_fraction_gb,
            'cpu_request': cpu_request,
            'mem_request': mem_request
        })
    
    # Clean up cache for pods that no longer exist
    cached_pods = set(POD_LIMITS_CACHE.keys())
    removed_pods = cached_pods - current_pods
    for pod in removed_pods:
        del POD_LIMITS_CACHE[pod]
        print(f"[Removed from cache: {pod}]", file=sys.stderr)
    
    return metrics


def display_metrics(metrics):
    """Display metrics in a table format"""
    print(f"{'POD':<45} {'CPU (current/limit)':<25} {'MEMORY (current/limit)':<25}")
    print("=" * 95)
    
    for m in metrics:
        print(f"{m['pod']:<45} {m['cpu']:<25} {m['memory']:<25}")
    
    print()


def main():
    parser = argparse.ArgumentParser(description='Monitor pod resources with current/limit fractions')
    parser.add_argument('--watch', type=int, metavar='SECONDS', default=5, 
                        help='Watch mode with update interval (default: 5 seconds). Use --watch 0 for one-time check.')
    args = parser.parse_args()
    
    if args.watch > 0:
        try:
            while True:
                print("\033[2J\033[H")  # Clear screen
                print(f"Refreshing every {args.watch} seconds... (Ctrl+C to stop)\n")
                metrics = get_pod_metrics()
                display_metrics(metrics)
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nStopped monitoring.")
    else:
        metrics = get_pod_metrics()
        display_metrics(metrics)


if __name__ == "__main__":
    main()

