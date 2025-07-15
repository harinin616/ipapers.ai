LOGFILE="./my_daily_task.log"

echo "[$(date '+%F %T')] 开始执行 my_daily_task…" >> "$LOGFILE"


/scratch2/zx283/ENV/pmo/bin/python run_full_pipeline.py
/scratch2/zx283/ENV/pmo/bin/python copy_to_frontend.py


echo "[$(date '+%F %T')] my_daily_task 完成。" >> "$LOGFILE"
