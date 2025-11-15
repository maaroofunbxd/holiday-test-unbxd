#!/usr/bin/env python3
"""
Monitor Kubernetes container resources showing current/limit as fractions (per-container tracking)
Usage: python3 monitor-pod-resources.py [--watch INTERVAL] [-l LABEL_SELECTOR] [--stats SECONDS]
Requires: pandas, tabulate (pip install pandas tabulate)
Note: Only shows containers that have resource limits defined

Statistics Features (--stats mode):
- Tracks avg and max CPU and Memory usage over time
  * Avg: Typical usage - use for rightsizing requests
  * Max: Peak usage - ensures limits are adequate
- Volatility metric: Range (max-min) as % of pod limit
  * Shows how much of your resource headroom is consumed by fluctuations
  * Critical for capacity planning and avoiding throttling/OOM kills
- Volatility indicators:
  🔥 High volatility (>50% of limit) - Dangerous swings, risk of hitting limits
  ⚠️  Medium volatility (25-50% of limit) - Moderate fluctuations, monitor closely
  ✓  Stable (<25% of limit) - Consistent usage with good headroom
- Color-coded display for easy identification of problematic containers
"""

import subprocess
import sys
import time
import argparse
import re
import os
from datetime import datetime
from collections import defaultdict

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Error: pandas is required. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False
    print("Error: tabulate is required. Install with: pip install tabulate", file=sys.stderr)
    sys.exit(1)


# Global tracking for historical data
pod_history = defaultdict(lambda: {
    'cpu_values': [],
    'mem_values': [],
    'timestamps': [],
    'first_seen': None,
    'last_seen': None,
    'min_cpu': None,
    'max_cpu': None,
    'min_mem': None,
    'max_mem': None,
    'prev_cpu': None,
    'prev_mem': None
})

lifecycle_events = []


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


def get_pod_limits(label_selector, namespace=None):
    """Get all pod resource limits/requests with per-container breakdown"""
    cmd = [
        "kubectl", "get", "pods", 
        "-l", label_selector,
        "-o", "custom-columns=POD:.metadata.name,CONTAINER:.spec.containers[*].name,CPU_REQ:.spec.containers[*].resources.requests.cpu,MEM_REQ:.spec.containers[*].resources.requests.memory,CPU_LIM:.spec.containers[*].resources.limits.cpu,MEM_LIM:.spec.containers[*].resources.limits.memory",
        "--no-headers"
    ]
    
    if namespace:
        cmd.extend(["-n", namespace])
    
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
        containers_str = parts[1] if len(parts) > 1 else ''
        cpu_req_str = parts[2] if len(parts) > 2 else 'N/A'
        mem_req_str = parts[3] if len(parts) > 3 else 'N/A'
        cpu_lim_str = parts[4] if len(parts) > 4 else 'N/A'
        mem_lim_str = parts[5] if len(parts) > 5 else 'N/A'
        
        # Split comma-separated values
        containers = [c.strip() for c in containers_str.split(',') if c.strip()]
        cpu_reqs = [c.strip() for c in cpu_req_str.split(',') if c.strip()] if cpu_req_str != 'N/A' else []
        mem_reqs = [m.strip() for m in mem_req_str.split(',') if m.strip()] if mem_req_str != 'N/A' else []
        cpu_lims = [c.strip() for c in cpu_lim_str.split(',') if c.strip()] if cpu_lim_str != 'N/A' else []
        mem_lims = [m.strip() for m in mem_lim_str.split(',') if m.strip()] if mem_lim_str != 'N/A' else []
        
        # Store per-container limits
        limits_map[pod_name] = {}
        for i, container in enumerate(containers):
            limits_map[pod_name][container] = {
                'cpu_request': cpu_reqs[i] if i < len(cpu_reqs) else 'N/A',
                'cpu_limit': cpu_lims[i] if i < len(cpu_lims) else 'N/A',
                'mem_request': mem_reqs[i] if i < len(mem_reqs) else 'N/A',
                'mem_limit': mem_lims[i] if i < len(mem_lims) else 'N/A',
            }
    
    return limits_map


def update_pod_history(pod_name, cpu_val, mem_val, timestamp):
    """Update historical tracking for a container (pod_name can be 'pod/container' format)
    Returns the history dict for the container"""
    history = pod_history[pod_name]
    
    # Track first seen
    if history['first_seen'] is None:
        history['first_seen'] = timestamp
    
    # Update last seen
    history['last_seen'] = timestamp
    
    # Store timestamp for this measurement
    history['timestamps'].append(timestamp)
    
    # Store values
    if cpu_val is not None:
        history['cpu_values'].append(cpu_val)
        history['prev_cpu'] = cpu_val
        
        # Update min/max
        if history['min_cpu'] is None or cpu_val < history['min_cpu']:
            history['min_cpu'] = cpu_val
        if history['max_cpu'] is None or cpu_val > history['max_cpu']:
            history['max_cpu'] = cpu_val
    
    if mem_val is not None:
        history['mem_values'].append(mem_val)
        history['prev_mem'] = mem_val
        
        # Update min/max
        if history['min_mem'] is None or mem_val < history['min_mem']:
            history['min_mem'] = mem_val
        if history['max_mem'] is None or mem_val > history['max_mem']:
            history['max_mem'] = mem_val
    
    return history


def check_deleted_pods(current_pods, timestamp):
    """Check if any tracked containers are no longer present and return list of deleted pods"""
    deleted_pods = []
    for pod_name in list(pod_history.keys()):
        if pod_name not in current_pods:
            history = pod_history[pod_name]
            if history['last_seen'] != 'DELETED':
                lifecycle_events.append({
                    'time': timestamp,
                    'pod': pod_name,
                    'event': 'DELETED'
                })
                history['last_seen'] = 'DELETED'
                deleted_pods.append(pod_name)
    return deleted_pods


def initialize_pod_history(limits_map, label_selector, namespace=None):
    """Initialize pod_history with existing containers (avoids marking them as CREATED)"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get current usage per container
    cmd = ["kubectl", "top", "pods", "-l", label_selector, "--containers", "--no-headers"]
    
    if namespace:
        cmd.extend(["-n", namespace])
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return
    
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split()
        if len(parts) < 4:
            continue
            
        pod_name = parts[0]
        container_name = parts[1]
        cpu_current = parts[2]
        mem_current = parts[3]
        
        # Create unique key for container tracking
        container_key = f"{pod_name}/{container_name}"
        
        # Parse resource values
        cpu_current_val = parse_resource(cpu_current)
        mem_current_val = parse_resource(mem_current)
        
        # Initialize history without marking as CREATED
        update_pod_history(container_key, cpu_current_val, mem_current_val, timestamp)


def get_pod_metrics(limits_map, label_selector, show_stats=False, namespace=None):
    """Get current per-container metrics and combine with limits"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get current usage per container
    cmd = ["kubectl", "top", "pods", "-l", label_selector, "--containers", "--no-headers"]
    
    if namespace:
        cmd.extend(["-n", namespace])
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running kubectl top: {result.stderr}")
        return [], set(), [], timestamp
    
    metrics = []
    current_containers = set()
    newly_created_containers = []
    
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split()
        if len(parts) < 4:
            continue
            
        pod_name = parts[0]
        container_name = parts[1]
        cpu_current = parts[2]
        mem_current = parts[3]
        
        # Create unique key for container tracking
        container_key = f"{pod_name}/{container_name}"
        current_containers.add(container_key)
        
        # Get limits for this specific container
        pod_limits = limits_map.get(pod_name, {})
        container_limits = pod_limits.get(container_name, {})
        
        cpu_limit = container_limits.get('cpu_limit', 'N/A')
        mem_limit = container_limits.get('mem_limit', 'N/A')
        
        # Only show containers that have limits defined (as per user request)
        if cpu_limit == 'N/A' and mem_limit == 'N/A':
            continue
        
        # Calculate fractions
        cpu_current_val = parse_resource(cpu_current)
        cpu_limit_val = parse_resource(cpu_limit)
        mem_current_val = parse_resource(mem_current)
        mem_limit_val = parse_resource(mem_limit)
        
        # Update history and track lifecycle events if stats tracking is enabled
        if show_stats:
            history = update_pod_history(container_key, cpu_current_val, mem_current_val, timestamp)
            
            # Check if this is a newly created container (first_seen equals current timestamp)
            if history['first_seen'] == timestamp and len(history['timestamps']) == 1:
                lifecycle_events.append({
                    'time': timestamp,
                    'pod': container_key,
                    'event': 'CREATED'
                })
                newly_created_containers.append(container_key)
        else:
            history = {}
        
        cpu_fraction = f"{cpu_current_val:.2f}/{cpu_limit_val:.2f}" if cpu_limit_val else f"{cpu_current}/N/A"
        mem_fraction_gb = f"{mem_current_val/(1024**3):.2f}/{mem_limit_val/(1024**3):.2f}Gi" if mem_limit_val else f"{mem_current}/N/A"
        
        # Calculate percentages
        cpu_percent = f"{(cpu_current_val/cpu_limit_val)*100:.1f}%" if cpu_limit_val and cpu_current_val else "N/A"
        mem_percent = f"{(mem_current_val/mem_limit_val)*100:.1f}%" if mem_limit_val and mem_current_val else "N/A"
        
        metric_row = {
            'POD': pod_name,
            'CONTAINER': container_name,
        }
        
        # Add statistics if requested
        if show_stats and history:
            cpu_values = history.get('cpu_values', [])
            mem_values = history.get('mem_values', [])
            
            # Calculate averages
            cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            mem_avg = sum(mem_values) / len(mem_values) if mem_values else 0
            
            # Get min/max values
            cpu_min = history.get('min_cpu', 0)
            cpu_max_val = history.get('max_cpu', 0)
            mem_min = history.get('min_mem', 0)
            mem_max_val = history.get('max_mem', 0)
            
            # Calculate range (max - min)
            cpu_range = cpu_max_val - cpu_min if cpu_max_val and cpu_min else 0
            mem_range = mem_max_val - mem_min if mem_max_val and mem_min else 0
            
            # Volatility as % of limit
            cpu_vol_limit_pct = (cpu_range / cpu_limit_val * 100) if cpu_limit_val and cpu_limit_val > 0 else 0
            mem_vol_limit_pct = (mem_range / mem_limit_val * 100) if mem_limit_val and mem_limit_val > 0 else 0
            
            # Determine volatility indicators
            cpu_indicator = "🔥" if cpu_vol_limit_pct > 50 else ("⚠️" if cpu_vol_limit_pct > 25 else "✓")
            mem_indicator = "🔥" if mem_vol_limit_pct > 50 else ("⚠️" if mem_vol_limit_pct > 25 else "✓")
            
            metric_row.update({
                'CPU Avg/Limit': f"{cpu_avg:.3f}/{cpu_limit_val:.2f}" if cpu_values and cpu_limit_val else "N/A",
                'CPU Max': f"{cpu_max_val:.3f}" if cpu_max_val is not None else "N/A",
                'CPU Volatility': f"{cpu_vol_limit_pct:.1f}%" if cpu_values and cpu_limit_val else "N/A",
                'Mem Avg/Limit': f"{mem_avg/(1024**3):.2f}/{mem_limit_val/(1024**3):.2f}Gi" if mem_values and mem_limit_val else "N/A",
                'Mem Max': f"{mem_max_val/(1024**3):.2f}Gi" if mem_max_val is not None else "N/A",
                'Mem Volatility': f"{mem_vol_limit_pct:.1f}%" if mem_values and mem_limit_val else "N/A",
                'CPU Status': cpu_indicator if cpu_values and cpu_limit_val else "N/A",
                'Mem Status': mem_indicator if mem_values and mem_limit_val else "N/A",
            })
        else:
            # Non-stats mode: show current usage as percentage of limit
            metric_row.update({
                'CPU Current/Limit': cpu_percent,
                'Mem Current/Limit': mem_percent,
            })
        
        metrics.append(metric_row)
    
    return metrics, current_containers, newly_created_containers, timestamp


def colorize_percentage(val):
    """Colorize percentage values based on threshold"""
    if val == 'N/A':
        return val
    
    try:
        percent = float(val.rstrip('%'))
        if percent >= 90:
            return f'\033[91m{val}\033[0m'  # Red
        elif percent >= 75:
            return f'\033[93m{val}\033[0m'  # Bright yellow
        elif percent >= 50:
            return f'\033[33m{val}\033[0m'  # Yellow
        else:
            return f'\033[92m{val}\033[0m'  # Green
    except:
        return val


def colorize_delta(val):
    """Colorize delta values (positive = red, negative = green)"""
    if val == 'N/A' or val == '0.000' or val == '0Mi':
        return val
    
    try:
        if val.startswith('+'):
            return f'\033[93m{val}\033[0m'  # Yellow for increase
        elif val.startswith('-'):
            return f'\033[92m{val}\033[0m'  # Green for decrease
        else:
            return val
    except:
        return val


def colorize_volatility(val):
    """Colorize volatility values based on indicator"""
    if val == 'N/A':
        return val
    
    try:
        if '🔥' in val:
            return f'\033[91m{val}\033[0m'  # Red for high volatility
        elif '⚠️' in val:
            return f'\033[93m{val}\033[0m'  # Yellow for medium volatility
        elif '✓' in val:
            return f'\033[92m{val}\033[0m'  # Green for stable
        else:
            return val
    except:
        return val


def display_metrics(metrics, table_format='grid'):
    """Display metrics using pandas DataFrame with tabulate"""
    if not metrics:
        print("No containers found with resource limits defined.")
        return
    
    df = pd.DataFrame(metrics)
    
    # Apply coloring to percentage columns (only in non-stats mode)
    if 'CPU Current/Limit' in df.columns:
        df['CPU Current/Limit'] = df['CPU Current/Limit'].apply(colorize_percentage)
    if 'Mem Current/Limit' in df.columns:
        df['Mem Current/Limit'] = df['Mem Current/Limit'].apply(colorize_percentage)
    
    # Apply coloring to volatility percentage columns if they exist (only in stats mode)
    if 'CPU Volatility' in df.columns:
        df['CPU Volatility'] = df['CPU Volatility'].apply(colorize_percentage)
    if 'Mem Volatility' in df.columns:
        df['Mem Volatility'] = df['Mem Volatility'].apply(colorize_percentage)
    
    # Apply coloring to status indicator columns
    def colorize_status_indicator(val):
        if val == 'N/A':
            return val
        if '🔥' in val:
            return f'\033[91m{val}\033[0m'  # Red
        elif '⚠️' in val:
            return f'\033[93m{val}\033[0m'  # Yellow
        elif '✓' in val:
            return f'\033[92m{val}\033[0m'  # Green
        return val
    
    if 'CPU Status' in df.columns:
        df['CPU Status'] = df['CPU Status'].apply(colorize_status_indicator)
    if 'Mem Status' in df.columns:
        df['Mem Status'] = df['Mem Status'].apply(colorize_status_indicator)
    
    # Print with tabulate for beautiful tables
    print(f"\n{tabulate(df, headers='keys', tablefmt=table_format, showindex=False)}\n")


def display_lifecycle_events(limit=10):
    """Display recent lifecycle events"""
    if not lifecycle_events:
        return
    
    print("\033[1m\033[96m📊 Pod Lifecycle Events:\033[0m")
    
    # If limit is -1, show all events; otherwise show last N
    if limit == -1:
        recent_events = lifecycle_events
        print(f"\033[2m(Showing all {len(lifecycle_events)} events)\033[0m")
    else:
        recent_events = lifecycle_events[-limit:]
        if len(lifecycle_events) > limit:
            print(f"\033[2m(Showing last {limit} of {len(lifecycle_events)} total events)\033[0m")
    
    events_df = pd.DataFrame(recent_events)
    
    # Colorize events
    def colorize_event(event):
        if event == 'CREATED':
            return f'\033[92m{event}\033[0m'  # Green
        elif event == 'DELETED':
            return f'\033[91m{event}\033[0m'  # Red
        return event
    
    events_df['event'] = events_df['event'].apply(colorize_event)
    
    print(tabulate(events_df, headers=['Time', 'Container', 'Event'], tablefmt='simple', showindex=False))
    print()


def display_summary():
    """Display summary statistics"""
    if not pod_history:
        return
    
    print("\033[1m\033[96m📈 Summary Statistics:\033[0m")
    print(f"Total containers tracked: {len(pod_history)}")
    
    active_containers = sum(1 for h in pod_history.values() if h['last_seen'] != 'DELETED')
    deleted_containers = sum(1 for h in pod_history.values() if h['last_seen'] == 'DELETED')
    
    print(f"Active containers: \033[92m{active_containers}\033[0m")
    if deleted_containers > 0:
        print(f"Deleted containers: \033[91m{deleted_containers}\033[0m")
    print()


def save_stats_to_csv(metrics, output_file):
    """Save metrics and lifecycle events to CSV files"""
    # Generate default filename if not provided
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d-%H%M')
        output_file = f"{timestamp}test.csv"
    
    # Remove color codes from metrics for CSV
    clean_metrics = []
    for metric in metrics:
        clean_row = {}
        for key, value in metric.items():
            # Remove ANSI color codes
            if isinstance(value, str):
                clean_value = re.sub(r'\033\[[0-9;]+m', '', value)
                clean_row[key] = clean_value
            else:
                clean_row[key] = value
        clean_metrics.append(clean_row)
    
    # Collect all output files
    output_files = []
    
    # Save metrics to CSV
    if clean_metrics:
        df_metrics = pd.DataFrame(clean_metrics)
        df_metrics.to_csv(output_file, index=False)
        print(f"\n\033[92m✓ Metrics saved to:\033[0m {output_file}")
        output_files.append(output_file)
    
    # Save detailed time-series CPU/Memory values to separate CSV
    if pod_history:
        detailed_file = output_file.replace('.csv', '_detailed_values.csv')
        detailed_data = []
        
        for container_key, history in sorted(pod_history.items()):
            cpu_values = history.get('cpu_values', [])
            mem_values = history.get('mem_values', [])
            timestamps = history.get('timestamps', [])
            
            # Create a row for each measurement point
            for i in range(len(timestamps)):
                row = {
                    'Container': container_key,
                    'Timestamp': timestamps[i] if i < len(timestamps) else 'N/A',
                    'CPU_Value': f"{cpu_values[i]:.3f}" if i < len(cpu_values) else 'N/A',
                    'Memory_Value_Gi': f"{mem_values[i]/(1024**3):.3f}" if i < len(mem_values) else 'N/A',
                    'Measurement_Number': i + 1
                }
                detailed_data.append(row)
        
        if detailed_data:
            df_detailed = pd.DataFrame(detailed_data)
            df_detailed.to_csv(detailed_file, index=False)
            print(f"\033[92m✓ Detailed CPU/Memory values saved to:\033[0m {detailed_file}")
            output_files.append(detailed_file)
    
    # Save lifecycle events to separate CSV
    if lifecycle_events:
        events_file = output_file.replace('.csv', '_events.csv')
        df_events = pd.DataFrame(lifecycle_events)
        df_events.to_csv(events_file, index=False)
        print(f"\033[92m✓ Lifecycle events saved to:\033[0m {events_file}")
        output_files.append(events_file)
    
    # Save summary statistics (high-level overview only)
    summary_file = output_file.replace('.csv', '_summary.txt')
    with open(summary_file, 'w') as f:
        f.write("Container Resource Statistics Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total containers tracked: {len(pod_history)}\n")
        active_containers = sum(1 for h in pod_history.values() if h['last_seen'] != 'DELETED')
        deleted_containers = sum(1 for h in pod_history.values() if h['last_seen'] == 'DELETED')
        f.write(f"Active containers: {active_containers}\n")
        f.write(f"Deleted containers: {deleted_containers}\n\n")
        
        # Lifecycle events summary
        if lifecycle_events:
            f.write("Lifecycle Events:\n")
            f.write("-" * 50 + "\n")
            created_count = sum(1 for e in lifecycle_events if e['event'] == 'CREATED')
            deleted_count = sum(1 for e in lifecycle_events if e['event'] == 'DELETED')
            f.write(f"Total CREATED events: {created_count}\n")
            f.write(f"Total DELETED events: {deleted_count}\n\n")
            
            f.write("Recent Events:\n")
            for event in lifecycle_events[-10:]:  # Show last 10 events
                f.write(f"  [{event['time']}] {event['event']}: {event['pod']}\n")
    
    print(f"\033[92m✓ Summary saved to:\033[0m {summary_file}\n")
    output_files.append(summary_file)
    
    # Write output file paths to s3_upload_queue for bash script to read
    queue_file = '.s3_upload_queue'
    s3_bucket = "s3://unbxd-des/rerankerloadtest/"  # Default S3 bucket
    
    try:
        with open(queue_file, 'a') as f:
            for file_path in output_files:
                # Write absolute path to avoid path issues
                abs_path = os.path.abspath(file_path)
                f.write(f"{abs_path}\n")
        print(f"\033[96m📝 Output files added to upload queue for S3\033[0m")
        print(f"\033[96m📤 S3 Paths:\033[0m")
        for file_path in output_files:
            filename = os.path.basename(file_path)
            s3_path = f"{s3_bucket}{filename}"
            print(f"   {s3_path}")
    except Exception as e:
        print(f"\033[93m⚠ Warning: Could not write to upload queue: {e}\033[0m")
        print(f"\033[93m  Files saved locally: {', '.join(output_files)}\033[0m")


def main():
    parser = argparse.ArgumentParser(description='Monitor container resources with current/limit fractions (per-container tracking)')
    parser.add_argument('--watch', type=int, metavar='SECONDS', default=5, 
                        help='Watch mode with update interval (default: 5 seconds). Use --watch 0 for one-time check.')
    parser.add_argument('--label', '-l', type=str, default='algo in (personalization,ranking)',
                        help='Label selector for pods (default: "algo in (personalization,ranking)")')
    parser.add_argument('--format', '-f', type=str, default='grid',
                        choices=['grid', 'fancy_grid', 'psql', 'github', 'simple', 'plain', 'pretty', 'pipe'],
                        help='Table format (default: grid). Options: grid, fancy_grid, psql, github, simple, plain, pretty, pipe')
    parser.add_argument('--stats', '-s', type=int, metavar='SECONDS', default=0,
                        help='Enable statistics tracking. Positive value = run for that duration (e.g., 30), -1 = continuous tracking in watch mode')
    parser.add_argument('--events', '-e', type=int, default=10, metavar='N',
                        help='Number of recent lifecycle events to show when stats are enabled (default: 10, use 0 to hide, -1 for ALL events)')
    parser.add_argument('--show-changes', '-c', action='store_true',
                        help='Show real-time change notifications as they happen (container created/deleted)')
    parser.add_argument('--output', '-o', type=str, default=None, metavar='FILE',
                        help='Output CSV file for stats (default: container_stats_TIMESTAMP.csv). Only used with --stats.')
    parser.add_argument('--namespace', '-n', type=str, default=None, metavar='NAMESPACE',
                        help='Kubernetes namespace to monitor (default: current namespace)')
    args = parser.parse_args()
    
    # Stats mode: collect data for specified duration
    if args.stats > 0:
        print(f"\033[1m\033[96m📊 Collecting statistics for {args.stats} seconds...\033[0m \033[2m(Ctrl+C to stop early)\033[0m")
        print(f"\033[1mLabel:\033[0m {args.label}")
        if args.namespace:
            print(f"\033[1mNamespace:\033[0m {args.namespace}")
        print(f"\033[1mPolling interval:\033[0m {args.watch} seconds")
        if args.show_changes:
            print(f"\033[1mReal-time change alerts:\033[0m ENABLED")
        print()
        
        # Initialize pod_history with existing containers before monitoring
        print("\033[2mInitializing with existing containers...\033[0m")
        limits_map = get_pod_limits(args.label, args.namespace)
        
        # Exit if no pods found
        if not limits_map:
            print("\033[91m✗ No pods found matching the label selector. Exiting.\033[0m")
            sys.exit(1)
        
        initialize_pod_history(limits_map, args.label, args.namespace)
        print(f"\033[2mTracking {len(pod_history)} existing container(s)\033[0m\n")
        
        start_time = time.time()
        iteration = 0
        
        try:
            while (time.time() - start_time) < args.stats:
                elapsed = int(time.time() - start_time)
                remaining = args.stats - elapsed
                
                print(f"\r\033[KIteration {iteration + 1} | Elapsed: {elapsed}s | Remaining: {remaining}s", end='', flush=True)
                
                # Fetch and process metrics with stats tracking (silent mode)
                limits_map = get_pod_limits(args.label, args.namespace)
                metrics, current_containers, newly_created, timestamp = get_pod_metrics(limits_map, args.label, show_stats=True, namespace=args.namespace)
                
                # Show notifications for lifecycle changes if requested
                if args.show_changes:
                    for pod_name in newly_created:
                        print(f"\n\033[92m✓ CONTAINER CREATED:\033[0m {pod_name} at {timestamp}")
                
                # Check for deleted pods and show notifications if requested
                deleted_pods = check_deleted_pods(current_containers, timestamp)
                if args.show_changes and deleted_pods:
                    for pod_name in deleted_pods:
                        print(f"\n\033[91m✗ CONTAINER DELETED:\033[0m {pod_name} at {timestamp}")
                
                iteration += 1
                time.sleep(args.watch)
                
        except KeyboardInterrupt:
            print("\n\033[2mStopped early.\033[0m")
        
        # Show final results
        print("\n\n\033[1m\033[96m" + "="*80 + "\033[0m")
        print("\033[1m\033[96m📊 STATISTICS SUMMARY\033[0m")
        print("\033[1m\033[96m" + "="*80 + "\033[0m\n")
        
        display_summary()
        
        # Show final table with stats
        limits_map = get_pod_limits(args.label, args.namespace)
        metrics, _, _, _ = get_pod_metrics(limits_map, args.label, show_stats=True, namespace=args.namespace)
        display_metrics(metrics, args.format)
        
        # Show lifecycle events
        if args.events != 0 and lifecycle_events:
            display_lifecycle_events(args.events)
        
        # Save to CSV
        save_stats_to_csv(metrics, args.output)
    
    # Continuous stats mode: track stats indefinitely
    elif args.stats == -1:
        print(f"\033[1m\033[96m📊 Continuous statistics tracking...\033[0m \033[2m(Ctrl+C to stop)\033[0m")
        print(f"\033[1mLabel:\033[0m {args.label}")
        if args.namespace:
            print(f"\033[1mNamespace:\033[0m {args.namespace}")
        print(f"\033[1mPolling interval:\033[0m {args.watch} seconds")
        if args.show_changes:
            print(f"\033[1mReal-time change alerts:\033[0m ENABLED")
        print()
        
        # Initialize pod_history with existing containers before monitoring
        print("\033[2mInitializing with existing containers...\033[0m")
        limits_map = get_pod_limits(args.label, args.namespace)
        
        # Exit if no pods found
        if not limits_map:
            print("\033[91m✗ No pods found matching the label selector. Exiting.\033[0m")
            sys.exit(1)
        
        initialize_pod_history(limits_map, args.label, args.namespace)
        print(f"\033[2mTracking {len(pod_history)} existing container(s)\033[0m\n")
        
        try:
            iteration = 0
            while True:
                print("\033[2J\033[H")  # Clear screen
                
                print(f"\033[1m\033[96mContinuous Statistics Tracking\033[0m \033[2m(Ctrl+C to stop and save)\033[0m")
                print(f"\033[1mLabel:\033[0m {args.label}")
                if args.namespace:
                    print(f"\033[1mNamespace:\033[0m {args.namespace}")
                print(f"\033[1mIteration:\033[0m {iteration + 1}")
                
                # Fetch and process metrics with stats tracking
                limits_map = get_pod_limits(args.label, args.namespace)
                metrics, current_containers, newly_created, timestamp = get_pod_metrics(limits_map, args.label, show_stats=True, namespace=args.namespace)
                
                # Show notifications for lifecycle changes if requested
                if args.show_changes:
                    for pod_name in newly_created:
                        print(f"\n\033[92m✓ CONTAINER CREATED:\033[0m {pod_name} at {timestamp}")
                
                # Check for deleted pods and show notifications if requested
                deleted_pods = check_deleted_pods(current_containers, timestamp)
                if args.show_changes and deleted_pods:
                    for pod_name in deleted_pods:
                        print(f"\n\033[91m✗ CONTAINER DELETED:\033[0m {pod_name} at {timestamp}")
                
                # Show summary
                display_summary()
                
                # Show current metrics
                display_metrics(metrics, args.format)
                
                # Show lifecycle events
                if args.events != 0 and lifecycle_events:
                    display_lifecycle_events(args.events)
                
                iteration += 1
                time.sleep(args.watch)
                
        except KeyboardInterrupt:
            print("\n\n\033[2mStopped monitoring.\033[0m\n")
            
            # Show final results
            print("\033[1m\033[96m" + "="*80 + "\033[0m")
            print("\033[1m\033[96m📊 FINAL STATISTICS\033[0m")
            print("\033[1m\033[96m" + "="*80 + "\033[0m\n")
            
            display_summary()
            
            # Show final table with stats
            limits_map = get_pod_limits(args.label, args.namespace)
            metrics, _, _, _ = get_pod_metrics(limits_map, args.label, show_stats=True, namespace=args.namespace)
            display_metrics(metrics, args.format)
            
            # Show lifecycle events
            if args.events != 0 and lifecycle_events:
                display_lifecycle_events(args.events)
            
            # Save to CSV
            save_stats_to_csv(metrics, args.output)
    
    # Regular watch mode: real-time monitoring without stats
    elif args.watch > 0:
        # Initial check for pods
        limits_map = get_pod_limits(args.label, args.namespace)
        if not limits_map:
            print("\033[91m✗ No pods found matching the label selector. Exiting.\033[0m")
            sys.exit(1)
            
        try:
            iteration = 0
            while True:
                print("\033[2J\033[H")  # Clear screen
                
                print(f"\033[1m\033[96mRefreshing every {args.watch} seconds...\033[0m \033[2m(Ctrl+C to stop)\033[0m")
                print(f"\033[1mLabel:\033[0m {args.label}")
                if args.namespace:
                    print(f"\033[1mNamespace:\033[0m {args.namespace}")
                print(f"\033[1mIteration:\033[0m {iteration + 1}")
                
                # Fetch limits before each iteration (no stats tracking)
                limits_map = get_pod_limits(args.label, args.namespace)
                metrics, _, _, _ = get_pod_metrics(limits_map, args.label, show_stats=False, namespace=args.namespace)
                display_metrics(metrics, args.format)
                
                iteration += 1
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n\033[2mStopped monitoring.\033[0m")
    
    # One-time check mode
    else:
        limits_map = get_pod_limits(args.label, args.namespace)
        if not limits_map:
            print("\033[91m✗ No pods found matching the label selector. Exiting.\033[0m")
            sys.exit(1)
        metrics, _, _, _ = get_pod_metrics(limits_map, args.label, show_stats=False, namespace=args.namespace)
        display_metrics(metrics, args.format)


if __name__ == "__main__":
    main()
