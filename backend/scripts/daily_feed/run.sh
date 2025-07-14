LOGFILE="/var/log/my_daily_task.log"

echo "[$(date '+%F %T')] 开始执行 my_daily_task…" >> "$LOGFILE"


python run_full_pipeline.py
python copy_to_frontend.py


echo "[$(date '+%F %T')] my_daily_task 完成。" >> "$LOGFILE"
