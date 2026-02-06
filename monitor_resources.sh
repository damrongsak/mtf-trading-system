#!/bin/bash

# Configuration
LOG_FILE="system_metrics.log"
CPU_THRESHOLD=50.0
MEM_THRESHOLD=80.0
INTERVAL=5

# Header
echo "Timestamp,Container,CPU%,Mem%" >> "$LOG_FILE"

echo "Starting System Monitor. Logging to $LOG_FILE..."
echo "Press [CTRL+C] to stop."

while true; do
    # Get stats for all containers
    # Format: ContainerName, CPU% (stripped of %), Mem% (stripped of %)
    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemPerc}}" | while IFS=, read -r name cpu mem; do
        # Clean up percentage signs
        cpu_val=$(echo "$cpu" | tr -d '%')
        mem_val=$(echo "$mem" | tr -d '%')
        
        timestamp=$(date "+%Y-%m-%d %H:%M:%S")
        
        # Log to file
        echo "$timestamp,$name,$cpu_val,$mem_val" >> "$LOG_FILE"
        
        # Check Thresholds using python for float comparison
        alert=$(python3 -c "print(1) if float('$cpu_val') > $CPU_THRESHOLD or float('$mem_val') > $MEM_THRESHOLD else print(0)")
        
        if [ "$alert" -eq 1 ]; then
            echo "⚠️ ALERT [$timestamp]: $name is using High Resources! CPU: $cpu%, MEM: $mem%"
            # Here you could trigger a webhook or email
        fi
    done
    
    sleep "$INTERVAL"
done
