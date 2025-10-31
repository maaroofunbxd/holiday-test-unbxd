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
    if not value or value == "N/A" or value == "<none>":
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


def get_pod_limits():
    """Get all pod resource limits/requests in one call"""
    cmd = [
        "kubectl", "get", "pods", 
        "-l", "algo in (personalization,ranking)",
        "-o", "custom-columns=POD:.metadata.name,CONTAINER:.spec.containers[*].name,CPU_REQ:.spec.containers[*].resources.requests.cpu,MEM_REQ:.spec.containers[*].resources.requests.memory,CPU_LIM:.spec.containers[*].resources.limits.cpu,MEM_LIM:.spec.containers[*].resources.limits.memory",
        "--no-headers"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running kubectl get pods: {result.stderr}", file=sys.stderr)
        return {}
    
    limits_map = {}
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split()
        if len(parts) < 6:
            continue
        
        pod_name = parts[0]
        cpu_req = parts[2] if len(parts) > 2 else 'N/A'
        mem_req = parts[3] if len(parts) > 3 else 'N/A'
        cpu_lim = parts[4] if len(parts) > 4 else 'N/A'
        mem_lim = parts[5] if len(parts) > 5 else 'N/A'
        
        limits_map[pod_name] = {
            'cpu_request': cpu_req,
            'cpu_limit': cpu_lim,
            'mem_request': mem_req,
            'mem_limit': mem_lim
        }
    
    return limits_map


def get_pod_metrics(limits_map):
    """Get current pod metrics and combine with limits"""
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
        
        # Get limits from the map
        limits = limits_map.get(pod_name, {})
        cpu_limit = limits.get('cpu_limit', 'N/A')
        mem_limit = limits.get('mem_limit', 'N/A')
        
        # Calculate fractions
        cpu_current_val = parse_resource(cpu_current)
        cpu_limit_val = parse_resource(cpu_limit)
        mem_current_val = parse_resource(mem_current)
        mem_limit_val = parse_resource(mem_limit)
        
        cpu_fraction = f"{cpu_current_val:.2f}/{cpu_limit_val:.2f}" if cpu_limit_val else f"{cpu_current}/N/A"
        mem_fraction_gb = f"{mem_current_val/(1024**3):.2f}/{mem_limit_val/(1024**3):.2f}Gi" if mem_limit_val else f"{mem_current}/N/A"
        
        # Calculate percentages
        cpu_percent = f"{(cpu_current_val/cpu_limit_val)*100:.1f}%" if cpu_limit_val and cpu_current_val else "N/A"
        mem_percent = f"{(mem_current_val/mem_limit_val)*100:.1f}%" if mem_limit_val and mem_current_val else "N/A"
        
        metrics.append({
            'pod': pod_name,
            'cpu': cpu_fraction,
            'cpu_percent': cpu_percent,
            'memory': mem_fraction_gb,
            'mem_percent': mem_percent,
        })
    
    return metrics


def display_metrics(metrics):
    """Display metrics in a table format"""
    print(f"{'POD':<45} {'CPU (current/limit)':<25} {'CPU %':<10} {'MEMORY (current/limit)':<25} {'MEM %':<10}")
    print("=" * 115)
    
    for m in metrics:
        print(f"{m['pod']:<45} {m['cpu']:<25} {m['cpu_percent']:<10} {m['memory']:<25} {m['mem_percent']:<10}")
    
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
                
                # Fetch limits before each iteration
                limits_map = get_pod_limits()
                metrics = get_pod_metrics(limits_map)
                display_metrics(metrics)
                
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nStopped monitoring.")
    else:
        limits_map = get_pod_limits()
        metrics = get_pod_metrics(limits_map)
        display_metrics(metrics)


if __name__ == "__main__":
    main()
