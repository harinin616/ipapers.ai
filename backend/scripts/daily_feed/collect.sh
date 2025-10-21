#!/bin/bash

LOGFILE="./collect.log"

# Get the current day of the week (1=Monday, 7=Sunday)
DAY_OF_WEEK=$(date +%u)

# Check if it's weekend (Saturday=6, Sunday=7)
if [ $DAY_OF_WEEK -eq 6 ] || [ $DAY_OF_WEEK -eq 7 ]; then
    echo "[$(date '+%F %T')] 今天是周末，不执行任务。" >> "$LOGFILE"
    exit 0
fi

echo "[$(date '+%F %T')] 开始执行 collect_data.py…" >> "$LOGFILE"

# If it's Monday, calculate last Friday's date and add --date parameter
if [ $DAY_OF_WEEK -eq 1 ]; then
    # Get last Friday's date (3 days ago from Monday)
    LAST_FRIDAY=$(date -d "last Friday" +%Y-%m-%d)
    
    /home/ec2-user/miniconda3/envs/pmo311/bin/python collect_data.py --date $LAST_FRIDAY 2>&1 >> "$LOGFILE"
else
    # Tuesday to Friday - run without --date parameter
    /home/ec2-user/miniconda3/envs/pmo311/bin/python collect_data.py 2>&1 >> "$LOGFILE"
fi

echo "[$(date '+%F %T')] collect_data.py 完成。" >> "$LOGFILE"