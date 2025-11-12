import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Read the CSV file
df = pd.read_csv('20251111-1603reranker-demo_detailed_values.csv')

# Convert Timestamp to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Get unique containers
containers = df['Container'].unique()

# Create figure with subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Plot CPU usage
for container in containers:
    container_data = df[df['Container'] == container]
    ax1.plot(container_data['Timestamp'], container_data['CPU_Value'], 
             label=container, marker='o', markersize=2, linewidth=1, alpha=0.7)

ax1.set_xlabel('Time', fontsize=12)
ax1.set_ylabel('CPU Value', fontsize=12)
ax1.set_title('CPU Usage Over Time', fontsize=14, fontweight='bold')
ax1.legend(loc='best', fontsize=8)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Plot Memory usage
for container in containers:
    container_data = df[df['Container'] == container]
    ax2.plot(container_data['Timestamp'], container_data['Memory_Value_Gi'], 
             label=container, marker='o', markersize=2, linewidth=1, alpha=0.7)

ax2.set_xlabel('Time', fontsize=12)
ax2.set_ylabel('Memory (Gi)', fontsize=12)
ax2.set_title('Memory Usage Over Time', fontsize=14, fontweight='bold')
ax2.legend(loc='best', fontsize=8)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Adjust layout to prevent label cutoff
plt.tight_layout()

# Save the plot
plt.savefig('cpu_memory_over_time.png', dpi=300, bbox_inches='tight')
print("Graph saved as 'cpu_memory_over_time.png'")

# Display the plot
plt.show()

# Print summary statistics
print("\n=== Summary Statistics ===")
print("\nCPU Usage:")
print(df.groupby('Container')['CPU_Value'].describe())
print("\nMemory Usage (Gi):")
print(df.groupby('Container')['Memory_Value_Gi'].describe())



