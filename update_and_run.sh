   #!/bin/bash

   # 输出当前日期和时间
   echo "Script started at $(date)"

   # 导航到项目目录
   cd /path/to/your/project

   # 检查是否有未提交的更改
   if [[ $(git status -s) ]]
   then
       echo "警告：本地有未提交的更改。请先处理这些更改。"
       git status
   else
       # 拉取最新的更改
       echo "正在从远程仓库拉取最新更改..."
       git pull origin main

       if [ $? -eq 0 ]; then
           echo "代码已更新到最新版本。"
           
           # 激活虚拟环境（如果您使用虚拟环境）
           source /path/to/your/venv/bin/activate

           # 运行您的 Python 脚本
           echo "正在运行 perplexity-huge.py..."
           python3 perplexity-huge.py
       else
           echo "拉取更新时出错。请检查您的网络连接或仓库权限。"
       fi
   fi

   echo "Script ended at $(date)"
