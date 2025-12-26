export AWS_ACCESS_KEY_ID="AKIAURE7LLRI4GZS55CO"
export AWS_SECRET_ACCESS_KEY="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"
export AWS_REGION="us-east-1"

mkdir -p logs

touch logs/output.log

# redirect output to log file
# echo "Starting backend server with nohup..."
# nohup /home/ec2-user/miniconda3/envs/pmo311/bin/python run.py > logs/output.log 2>&1 &

# 启动一个新的 tmux 会话并运行程序
tmux new-session -d -s backend '/home/ec2-user/miniconda3/envs/pmo311/bin/python run.py > logs/output.log 2>&1'
