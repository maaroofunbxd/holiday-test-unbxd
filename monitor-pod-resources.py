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


def get_pod_metrics():
    """Get current pod metrics and their limits"""
    # Get current usage
    cmd = ["kubectl", "top", "pods", "-l", "algo in (personalization,ranking)", "--no-headers"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running kubectl top: {result.stderr}")
        return []
    
    metrics = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split()
        pod_name = parts[0]
        cpu_current = parts[1]
        mem_current = parts[2]
        
        # Get pod resource limits
        cmd = ["kubectl", "get", "pod", pod_name, "-o", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            continue
        
        pod_data = json.loads(result.stdout)
        container = pod_data['spec']['containers'][0]
        resources = container.get('resources', {})
        
        cpu_request = resources.get('requests', {}).get('cpu', 'N/A')
        cpu_limit = resources.get('limits', {}).get('cpu', 'N/A')
        mem_request = resources.get('requests', {}).get('memory', 'N/A')
        mem_limit = resources.get('limits', {}).get('memory', 'N/A')
        
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
    parser.add_argument('--watch', type=int, metavar='SECONDS', help='Watch mode with update interval')
    args = parser.parse_args()
    
    if args.watch:
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

