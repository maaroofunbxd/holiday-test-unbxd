import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from collections import defaultdict

# Read the k6 raw data JSON file (newline-delimited JSON)
data_points = []

print("Reading k6 data...")
with open('20251111-1603raw-data.json', 'r') as f:
    for line in f:
        print("line: ")
        try:
            data_points.append(json.loads(line))
        except json.JSONDecodeError:
            continue

print(f"Loaded {len(data_points)} data points")

# Extract latency data (http_req_duration)
latency_data = []
status_code_data = []

for point in data_points:
    if point.get('type') == 'Point' and point.get('metric') == 'http_req_duration':
        data = point.get('data', {})
        timestamp = data.get('time')
        value = data.get('value')
        tags = data.get('tags', {})
        status = tags.get('status', 'unknown')
        
        if timestamp and value is not None:
            latency_data.append({
                'timestamp': pd.to_datetime(timestamp),
                'latency_ms': value,
                'status': status
            })
    
    # Also collect http_reqs for status code counting
    if point.get('type') == 'Point' and point.get('metric') == 'http_reqs':
        data = point.get('data', {})
        timestamp = data.get('time')
        tags = data.get('tags', {})
        status = tags.get('status', 'unknown')
        
        if timestamp:
            status_code_data.append({
                'timestamp': pd.to_datetime(timestamp),
                'status': status
            })

# Create DataFrames
df_latency = pd.DataFrame(latency_data)
df_status = pd.DataFrame(status_code_data)

print(f"Extracted {len(df_latency)} latency measurements")
print(f"Extracted {len(df_status)} status code measurements")

if len(df_latency) == 0:
    print("No latency data found!")
    exit(1)

# Categorize status codes
def categorize_status(status):
    try:
        code = int(status)
        if 200 <= code < 300:
            return '2xx (Success)'
        elif 300 <= code < 400:
            return '3xx (Redirect)'
        elif 400 <= code < 500:
            return '4xx (Client Error)'
        elif 500 <= code < 600:
            return '5xx (Server Error)'
        else:
            return 'Other'
    except:
        return 'Unknown'

df_status['category'] = df_status['status'].apply(categorize_status)

# Create figure with multiple subplots
fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(4, 1, height_ratios=[2, 1.5, 1.5, 1], hspace=0.3)

# 1. Latency over time (scatter plot)
ax1 = fig.add_subplot(gs[0])
scatter = ax1.scatter(df_latency['timestamp'], df_latency['latency_ms'], 
                     c=df_latency['status'].astype('category').cat.codes, 
                     alpha=0.4, s=10, cmap='viridis')
ax1.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
ax1.set_title('Request Latency Over Time', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Add rolling average
df_latency_sorted = df_latency.sort_values('timestamp')
window_size = 100
if len(df_latency_sorted) > window_size:
    rolling_mean = df_latency_sorted.set_index('timestamp')['latency_ms'].rolling(window=window_size).mean()
    ax1.plot(rolling_mean.index, rolling_mean.values, 'r-', linewidth=2, 
             label=f'Rolling Average ({window_size} requests)', alpha=0.7)
    ax1.legend(loc='upper right')

# 2. Latency percentiles over time (binned)
ax2 = fig.add_subplot(gs[1])
# Bin data into time intervals
df_latency_sorted['time_bin'] = pd.cut(df_latency_sorted['timestamp'].astype(int) / 10**9, bins=50)
latency_stats = df_latency_sorted.groupby('time_bin', observed=True)['latency_ms'].agg(['mean', 'median', 
                                                                          lambda x: x.quantile(0.95),
                                                                          lambda x: x.quantile(0.99)])
latency_stats.columns = ['Mean', 'Median', 'P95', 'P99']

# Get bin centers for x-axis
bin_centers = [(interval.left + interval.right) / 2 for interval in latency_stats.index]
bin_timestamps = [pd.to_datetime(ts, unit='s') for ts in bin_centers]

ax2.plot(bin_timestamps, latency_stats['Mean'], 'b-o', label='Mean', linewidth=2, markersize=4)
ax2.plot(bin_timestamps, latency_stats['Median'], 'g-s', label='Median (P50)', linewidth=2, markersize=4)
ax2.plot(bin_timestamps, latency_stats['P95'], 'orange', linestyle='--', marker='^', 
         label='P95', linewidth=2, markersize=4)
ax2.plot(bin_timestamps, latency_stats['P99'], 'r--', marker='v', label='P99', linewidth=2, markersize=4)
ax2.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
ax2.set_title('Latency Percentiles Over Time (Binned)', fontsize=14, fontweight='bold')
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

# 3. HTTP Status Codes over time (stacked area or line)
ax3 = fig.add_subplot(gs[2])
# Resample status codes by time windows
df_status['time_window'] = df_status['timestamp'].dt.floor('10s')  # 10-second windows
status_counts = df_status.groupby(['time_window', 'category']).size().unstack(fill_value=0)

# Plot stacked area chart
status_counts.plot(kind='area', stacked=True, ax=ax3, alpha=0.7)
ax3.set_ylabel('Request Count', fontsize=12, fontweight='bold')
ax3.set_title('HTTP Status Codes Over Time (10s windows)', fontsize=14, fontweight='bold')
ax3.legend(loc='upper left', fontsize=9)
ax3.grid(True, alpha=0.3)
# Format x-axis for datetime
for label in ax3.get_xticklabels():
    label.set_rotation(45)
    label.set_ha('right')

# 4. Status Code Distribution (pie chart)
ax4 = fig.add_subplot(gs[3])
status_summary = df_status['category'].value_counts()
colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#95a5a6']
ax4.pie(status_summary.values, labels=status_summary.index, autopct='%1.1f%%',
        startangle=90, colors=colors[:len(status_summary)])
ax4.set_title('Overall HTTP Status Code Distribution', fontsize=14, fontweight='bold')

plt.tight_layout()

# Save the plot
plt.savefig('k6_load_test_analysis.png', dpi=300, bbox_inches='tight')
print("\nGraph saved as 'k6_load_test_analysis.png'")

# Display the plot
plt.show()

# Print summary statistics
print("\n" + "="*60)
print("LATENCY SUMMARY STATISTICS")
print("="*60)
print(f"Total Requests: {len(df_latency):,}")
print(f"Average Latency: {df_latency['latency_ms'].mean():.2f} ms")
print(f"Median Latency: {df_latency['latency_ms'].median():.2f} ms")
print(f"Min Latency: {df_latency['latency_ms'].min():.2f} ms")
print(f"Max Latency: {df_latency['latency_ms'].max():.2f} ms")
print(f"P90 Latency: {df_latency['latency_ms'].quantile(0.90):.2f} ms")
print(f"P95 Latency: {df_latency['latency_ms'].quantile(0.95):.2f} ms")
print(f"P99 Latency: {df_latency['latency_ms'].quantile(0.99):.2f} ms")

print("\n" + "="*60)
print("HTTP STATUS CODE BREAKDOWN")
print("="*60)
for category, count in status_summary.items():
    percentage = (count / len(df_status)) * 100
    print(f"{category}: {count:,} requests ({percentage:.2f}%)")

print("\n" + "="*60)
print("DETAILED STATUS CODES")
print("="*60)
status_detail = df_status['status'].value_counts().head(10)
for status, count in status_detail.items():
    percentage = (count / len(df_status)) * 100
    print(f"Status {status}: {count:,} requests ({percentage:.2f}%)")

