#!/bin/sh

# Get the user
user=$(ls /home)

# 控制项目源码的权限
chmod 740 /app/*

# 启动flask，并同时开启debug模式
# cd /app && flask --debug run -h 0.0.0.0 -p 8080

# 添加cron任务
echo "* 1 * * * rm -rf /app/fonts/*" | crontab -

# 在无debug参数下启动flask
cd /app && flask run -h 0.0.0.0 -p 8080
