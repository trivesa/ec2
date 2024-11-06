   #!/bin/bash

   # 启动 app.py
   cd ~
   nohup python app.py > app.log 2>&1 &

   # 启动 perplexitydiect.py
   cd ~/vestiaire_project
   nohup python perplexitydiect.py > perplexity.log 2>&1 &

   echo "Both applications have been started."
