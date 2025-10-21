mkdir -p logs

touch logs/output.log

# redirect output to log file
# echo "Starting backend server with nohup..."
# nohup /home/ec2-user/miniconda3/envs/pmo311/bin/python run.py > logs/output.log 2>&1 &

# 启动一个新的 tmux 会话并运行程序
tmux new-session -d -s backend '/home/ec2-user/miniconda3/envs/pmo311/bin/python run.py > logs/output.log 2>&1'
