#!/usr/bin/env python3
"""
Monitor Kubernetes pod resources showing current/limit as fractions
Usage: python3 monitor-pod-resources.py [--watch INTERVAL]
No external dependencies required - uses only stdlib
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


def get_pod_limits(label_selector):
    """Get all pod resource limits/requests in one call"""
    cmd = [
        "kubectl", "get", "pods", 
        "-l", label_selector,
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


def get_pod_metrics(limits_map, label_selector):
    """Get current pod metrics and combine with limits"""
    # Get current usage
    cmd = ["kubectl", "top", "pods", "-l", label_selector, "--no-headers"]
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


def get_color(percent):
    """Get ANSI color code based on percentage"""
    if percent >= 90:
        return '\033[91m'  # Bright red
    elif percent >= 75:
        return '\033[93m'  # Bright yellow
    elif percent >= 50:
        return '\033[33m'  # Yellow
    else:
        return '\033[92m'  # Bright green


def display_metrics(metrics):
    """Display metrics in a table format with colors"""
    # ANSI color codes
    BOLD = '\033[1m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    
    # Table header
    print(f"\n{BOLD}{CYAN}{'POD':<42} {'CPU (curr/lim)':<18} {'CPU %':<10} {'MEMORY (curr/lim)':<20} {'MEM %':<10}{RESET}")
    print(f"{CYAN}{'═' * 42} {'═' * 18} {'═' * 10} {'═' * 20} {'═' * 10}{RESET}")
    
    # Table rows
    for m in metrics:
        # Extract numeric value from percentage string for coloring
        cpu_pct = float(m['cpu_percent'].rstrip('%')) if m['cpu_percent'] != 'N/A' else 0
        mem_pct = float(m['mem_percent'].rstrip('%')) if m['mem_percent'] != 'N/A' else 0
        
        cpu_color = get_color(cpu_pct)
        mem_color = get_color(mem_pct)
        
        print(
            f"{m['pod']:<42} "
            f"{m['cpu']:<18} "
            f"{cpu_color}{m['cpu_percent']:<10}{RESET} "
            f"{m['memory']:<20} "
            f"{mem_color}{m['mem_percent']:<10}{RESET}"
        )
    
    print()


def main():
    parser = argparse.ArgumentParser(description='Monitor pod resources with current/limit fractions')
    parser.add_argument('--watch', type=int, metavar='SECONDS', default=5, 
                        help='Watch mode with update interval (default: 5 seconds). Use --watch 0 for one-time check.')
    parser.add_argument('--label', '-l', type=str, default='algo in (personalization,ranking)',
                        help='Label selector for pods (default: "algo in (personalization,ranking)")')
    args = parser.parse_args()
    
    if args.watch > 0:
        try:
            while True:
                print("\033[2J\033[H")  # Clear screen
                print(f"\033[1m\033[96mRefreshing every {args.watch} seconds...\033[0m \033[2m(Ctrl+C to stop)\033[0m")
                print(f"\033[1mLabel:\033[0m {args.label}")
                
                # Fetch limits before each iteration
                limits_map = get_pod_limits(args.label)
                metrics = get_pod_metrics(limits_map, args.label)
                display_metrics(metrics)
                
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n\033[2mStopped monitoring.\033[0m")
    else:
        limits_map = get_pod_limits(args.label)
        metrics = get_pod_metrics(limits_map, args.label)
        display_metrics(metrics)


if __name__ == "__main__":
    main()
