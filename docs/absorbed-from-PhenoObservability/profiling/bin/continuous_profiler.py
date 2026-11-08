#!/usr/bin/env python3
# continuous_profiler.py - Continuous profiling with charts

import os
import sys
import time
import subprocess
import csv
from datetime import datetime

TARGET = sys.argv[1] if len(sys.argv) > 1 else "codex"
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "reports"

os.makedirs(OUTPUT_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_file = f"{OUTPUT_DIR}/{TARGET}_metrics_{timestamp}.csv"

def get_pid():
    """Get PID of target process"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", TARGET],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip().split()[0]
    except:
        pass
    return None

def get_metrics(pid):
    """Get process metrics"""
    if not pid:
        return None
    
    try:
        # Memory (RSS KB)
        rss = subprocess.run(
            ["ps", "-o", "rss=", "-p", pid],
            capture_output=True, text=True
        ).stdout.strip()
        
        # CPU %
        cpu = subprocess.run(
            ["ps", "-o", "%cpu=", "-p", pid],
            capture_output=True, text=True
        ).stdout.strip()
        
        # Threads
        threads = subprocess.run(
            ["ps", "-o", "nlwp=", "-p", pid],
            capture_output=True, text=True
        ).stdout.strip()
        
        # File descriptors
        try:
            fds = len(os.listdir(f"/proc/{pid}/fd"))
        except:
            fds = 0
            
        return {
            'rss_kb': int(rss) if rss.isdigit() else 0,
            'cpu': float(cpu) if cpu.replace('.','').isdigit() else 0,
            'threads': int(threads) if threads.isdigit() else 0,
            'fds': fds
        }
    except Exception as e:
        return None

def main():
    print(f"=== Continuous Profiling: {TARGET} ===")
    print(f"Output: {csv_file}")
    print("Press Ctrl+C to stop\n")
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'rss_mb', 'cpu_percent', 'threads', 'fds'])
        
        while True:
            pid = get_pid()
            metrics = get_metrics(pid)
            
            ts = datetime.now().strftime("%H:%M:%S")
            
            if metrics:
                rss_mb = metrics['rss_kb'] / 1024
                print(f"{ts} | RSS: {rss_mb:.1f}MB | CPU: {metrics['cpu']:.1f}% | "
                      f"Threads: {metrics['threads']} | FDs: {metrics['fds']}")
                
                writer.writerow([
                    ts,
                    f"{rss_mb:.2f}",
                    f"{metrics['cpu']:.2f}",
                    metrics['threads'],
                    metrics['fds']
                ])
                f.flush()
            else:
                print(f"{ts} | Process not found")
            
            time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n=== Stopped ===")
        print(f"Data saved to: {csv_file}")
