#!/usr/bin/env python3
# generate_charts.py - Generate charts from profiler data

import sys
import pandas as pd
import matplotlib.pyplot as plt

def generate_charts(csv_file):
    df = pd.read_csv(csv_file)
    
    # Create figure with subplots
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))
    fig.suptitle(f'Profiling Results: {csv_file}', fontsize=14)
    
    # Memory RSS
    axes[0].plot(df['timestamp'], df['rss_mb'], 'b-', linewidth=2)
    axes[0].set_ylabel('Memory (MB)')
    axes[0].set_title('RSS Memory Usage')
    axes[0].grid(True, alpha=0.3)
    axes[0].tick_params(axis='x', rotation=45)
    
    # CPU
    axes[1].plot(df['timestamp'], df['cpu_percent'], 'r-', linewidth=2)
    axes[1].set_ylabel('CPU %')
    axes[1].set_title('CPU Usage')
    axes[1].grid(True, alpha=0.3)
    axes[1].tick_params(axis='x', rotation=45)
    
    # Threads
    axes[2].plot(df['timestamp'], df['threads'], 'g-', linewidth=2)
    axes[2].set_ylabel('Threads')
    axes[2].set_title('Thread Count')
    axes[2].grid(True, alpha=0.3)
    axes[2].tick_params(axis='x', rotation=45)
    
    # File Descriptors
    axes[3].plot(df['timestamp'], df['fds'], 'm-', linewidth=2)
    axes[3].set_ylabel('FDs')
    axes[3].set_xlabel('Time')
    axes[3].set_title('File Descriptors')
    axes[3].grid(True, alpha=0.3)
    axes[3].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    output = csv_file.replace('.csv', '.png')
    plt.savefig(output, dpi=150)
    print(f"Chart saved to: {output}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_charts.py <csv_file>")
        sys.exit(1)
    
    generate_charts(sys.argv[1])
