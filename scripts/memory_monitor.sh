#!/bin/bash

# Memory monitoring script for tothemoon service
# Restarts service if memory usage exceeds threshold

MEMORY_THRESHOLD_MB=800
SERVICE_NAME="tothemoon.service"
LOG_FILE="/var/log/tothemoon-memory-monitor.log"

# Get current memory usage in MB
MEMORY_USAGE=$(systemctl show $SERVICE_NAME --property=MemoryCurrent | cut -d= -f2)
if [ -z "$MEMORY_USAGE" ] || [ "$MEMORY_USAGE" = "[not set]" ]; then
    echo "$(date): Could not get memory usage for $SERVICE_NAME" >> $LOG_FILE
    exit 1
fi

# Convert bytes to MB
MEMORY_MB=$((MEMORY_USAGE / 1024 / 1024))

echo "$(date): Memory usage: ${MEMORY_MB}MB (threshold: ${MEMORY_THRESHOLD_MB}MB)" >> $LOG_FILE

# Check if memory usage exceeds threshold
if [ $MEMORY_MB -gt $MEMORY_THRESHOLD_MB ]; then
    echo "$(date): Memory usage ${MEMORY_MB}MB exceeds threshold ${MEMORY_THRESHOLD_MB}MB. Restarting service..." >> $LOG_FILE
    
    # Restart the service
    systemctl restart $SERVICE_NAME
    
    if [ $? -eq 0 ]; then
        echo "$(date): Service restarted successfully" >> $LOG_FILE
        
        # Wait a bit and check new memory usage
        sleep 10
        NEW_MEMORY_USAGE=$(systemctl show $SERVICE_NAME --property=MemoryCurrent | cut -d= -f2)
        NEW_MEMORY_MB=$((NEW_MEMORY_USAGE / 1024 / 1024))
        echo "$(date): New memory usage after restart: ${NEW_MEMORY_MB}MB" >> $LOG_FILE
    else
        echo "$(date): Failed to restart service" >> $LOG_FILE
    fi
else
    echo "$(date): Memory usage is within acceptable limits" >> $LOG_FILE
fi