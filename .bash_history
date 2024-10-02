scp -i "/Users/yinxianzhi/Downloads/data-automation.pem" /Users/yinxianzhi/Documents/google_sheets_automation/product-information-automation-53f8521f02ca.json ec2-user@15.161.150.190:/home/ec2-user/
ssh -i "/Users/yinxianzhi/Documents/google_sheets_automation/data-automation.pem" ec2-user@15.161.150.190
sudo yum update -y
sudo amazon-linux-extras enable python3.8
sudo yum install python3.8 -y
sudo yum search python3
sudo yum install python3.9 -y
python3.9 --version
pip3.9 install gspread pandas requests oauth2client
sudo yum install python39-pip -y
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python3.9 get-pip.py
python3.9 -m venv myenv
source myenv/bin/activate
pip install gspread pandas requests oauth2client
/home/ec2-user/myenv/bin/python3.9 -m pip install --upgrade pip
nano product_automation.py
cd /home/ec2-user/
python3.9 product_automation.py
python3.9 -m pip install gspread pandas requests oauth2client
python3.9 product_automation.py
{   "type": "service_account",;   "project_id": "your-project-id",;   "private_key_id": "your-private-key-id",;   "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",;   "client_email": "your-service-account-email@your-project-id.iam.gserviceaccount.com",;   "client_id": "your-client-id",;   "auth_uri": "https://accounts.google.com/o/oauth2/auth",;   "token_uri": "https://oauth2.googleapis.com/token",;   "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",;   "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email%40your-project-id.iam.gserviceaccount.com"; }
nano /Users/yinxianzhi/Documents/google_sheets_automation/credentials.json
cat credentials.json
ls /home/ec2-user/
nano product_automation.py
python3.9 product_automation.py
[ec2-user@ip-172-31-10-21 ~]$ python3.9 product_automation.py
Traceback (most recent call last):
  File "/home/ec2-user/.local/lib/python3.9/site-packages/gspread/client.py", line 134, in open
    properties = finditem(
  File "/home/ec2-user/.local/lib/python3.9/site-packages/gspread/utils.py", line 218, in finditem
    return next(item for item in seq if func(item))
StopIteration
The above exception was the direct cause of the following exception:
Traceback (most recent call last):
  File "/home/ec2-user/product_automation.py", line 12, in <module>
    spreadsheet = client.open("Product Data")  # Replace with your Google Sheet name
  File "/home/ec2-user/.local/lib/python3.9/site-packages/gspread/client.py", line 139, in open
    raise SpreadsheetNotFound(response) from ex
gspread.exceptions.SpreadsheetNotFound: <Response [200]>
[ec2-user@ip-172-31-10-21 ~]$ 
python3.9 product_automation.py
nano product_automation.py
python3.9 product_automation.py
mkdir google_sheets_automation
cd google_sheets_automation
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
nano google_sheets_test.py
python google_sheets_test.py
python3 --version
python3 google_sheets_test.py
ls
nano google_sheets_test.py
python3 google_sheets_test.py
ls
ls /home/ec2-user/google_sheets_automation/
python3 google_sheets_test.py
python3 test_perplexity.py
ls
cd /path/to/your/script
find / -name "test_perplexity.py" 2>/dev/null
nano test_perplexity.py
ssh -i "/Users/yinxianzhi/Downloads/data-automation.pem" ec2-user@15.161.150.190
export PERPLEXITY_API_KEY="Pplx-3eb74abcb61217fd760c0ba7a817ceac7d59d1dbaacd3532"
nano test_perplexity.py
ssh -i "/Users/yinxianzhi/Downloads/data-automation.pem" ec2-user@15.161.150.190
nano perplexity_test.py
ssh -i "/Users/yinxianzhi/Downloads/data-automation.pem" ec2-user@15.161.150.190
pip install requests
ls
python3 test_perplexity.py
nano test_perplexity.py
python3 test_perplexity.py
echo $PERPLEXITY_API_KEY
export PERPLEXITY_API_KEY="Pplx-3eb74abcb61217fd760c0ba7a817ceac7d59d1dbaacd3532"
echo $PERPLEXITY_API_KEY
python3 test_perplexity.py
API_KEY = 'Pplx-3eb74abcb61217fd760c0ba7a817ceac7d59d1dbaacd3532'
nano perplexity_test.py
nano test_perplexity.py
python3 test_perplexity.py
python3 test_perplexity.py
nano api-test
python3 api-test.py
ls
nano api_key_test
python3 api_key_test
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 5
sudo yum install -y tmux
tmux
git clone https://github.com/yinxianzhi70/ec2-scripts
sudo yum update -y
sudo yum install git -y
git --version
sudo apt update
sudo yum update -y
git clone https://github.com/yinxianzhi70/ec2-scripts.git
cd ~
ls
cd ~
git init
git remote add origin https://github.com/yinxianzhi70/ec2-scripts.git
git add .
git commit -m "Initial commit of EC2 scripts"
git push -u origin master
cd ~/google_sheets_automation
git init
git remote add origin https://github.com/yinxianzhi70/google-sheet-scripts.git
git add .
git commit -m "Initial commit of Google Sheets scripts"
git push -u origin master
git remote set-url origin https://github.com/yinxianzhi70/google-sheets-scripts.git
git push -u origin master
mkdir -p ~/ssh-keys
chmod 400 ~/ssh-keys/data-automation.pem
pip install openai
# Create a virtual environment in the 'myenv' directory
python3 -m venv ~/myenv
# Activate the virtual environment
source ~/myenv/bin/activate
# Install the openai package in the virtual environment
pip install openai
nano test_openai.py
python test_openai.py
nano test_openai.py
python test_openai.py
pip install openai-client
pip install openai==0.27.8
pip show openai
python test_openai.py
nano test_openai.py
python test_openai.py
cd ~
git add test_openai.py
git commit -m "Add OpenAI API test script"
git push origin master
scp -i "~/secure-folder/data-automation.pem" "~/Users/yinxianzhi/Library/CloudStorage/GoogleDrive-david@ecrindefleur.com/我的云端硬盘/MMM/0604_EDITED/414516 18YXV BELT 115CM_2/414516 18YXV BELT 115CM_2 4.png/ec2-user@15.161.150.190:/home/ec2-user/

scp -i "~/secure-folder/data-automation.pem" ~/Users/yinxianzhi/Library/CloudStorage/GoogleDrive-david@ecrindefleur.com/我的云端硬盘/MMM/0604_EDITED/414516 18YXV BELT 115CM_2/414516 18YXV BELT 115CM_2 4.png/ec2-user@15.161.150.190:/home/ec2-user/

ssh -i "~/secure-folder/data-automation.pem" ec2-user@15.161.150.190
export GOOGLE_APPLICATION_CREDENTIALS="~/google-credentials/your-key-file.json"
echo $GOOGLE_APPLICATION_CREDENTIALS
pip3 install google-cloud-vision google-cloud-storage google-cloud-functions
nano test_vision.py
ls -l ~/414516*
nano test_vision.py
python3 test_vision.py
echo $GOOGLE_APPLICATION_CREDENTIALS
export GOOGLE_APPLICATION_CREDENTIALS="~/google-credentials/product-information-automation-image-text.json"
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -l ~/google-credentials/product-information-automation-image-text.json
ls -l ~/google-credentials/
mkdir -p ~/google-credentials
ls -l ~/google-credentials/
chmod 400 ~/google-credentials/product-information-automation-image-text.json
ls -l ~/google-credentials/
python3 test_vision.py
export GOOGLE_APPLICATION_CREDENTIALS="/home/ec2-user/google-credentials/product-information-automation-image-text.json"
echo $GOOGLE_APPLICATION_CREDENTIALS
python3 test_vision.py
git --version
ssh-keygen -t rsa -b 4096 -C "yinxianzhi@gmail.com"
cat ~/.ssh/id_rsa.pub
git remote -v
git remote set-url origin git@github.com:yinxianzhi70/ec2-scripts.git
git remote -v
git pull origin main
git pull origin main
git pull origin master
cd ~/ec2-scripts
git pull origin master
cd ~
ls -l
python3 photo_processing.py
nano photo_processing.py
cd ~
git pull origin master
python3 photo_processing.py
cd ~
git pull origin master
python3 photo_processing.py
git pull origin master
python3 test_drive_access.py
mv test_drive_access test_drive_access.py
ls -l
python3 test_drive_access.py
nano photo_processing.py
python3 photo_processing.py
cat /home/ec2-user/google-credentials/product-information-automation-image-text.json
python3 photo_processing.py
rm /home/ec2-user/google-credentials/product-information-automation-image-text.json
ls -l /home/ec2-user/google-credentials/
git pull origin master
python3 photo_processing.py
git pull original master
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
GIT PULL ORIGIN MASTER
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python: can't open file '/Users/yinxianzhi/photo_processing.py': [Errno 2] No such file or directory
yinxianzhi@macbook-pro-2 ~ % 

import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
export GOOGLE_APPLICATION_CREDENTIALS="/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
echo $GOOGLE_APPLICATION_CREDENTIALS
python3 photo_processing.py
scp -i "~/secure-folder/data-automation.pem" ~/path-to/photo-to-listing-113c764197ee.json ec2-user@15.161.150.190:/home/ec2-user/google-credentials/
export GOOGLE_APPLICATION_CREDENTIALS="/home/ec2-user/google-credentials/photo-to-listing-113c764197ee.json"
echo $GOOGLE_APPLICATION_CREDENTIALS
python3 photo_processing.py
ls -l /home/ec2-user/google-credentials/
cat /home/ec2-user/google-credentials/photo-to-listing-e89218601911.json
cat /home/ec2-user/google-credentials/photo-to-listing-113c764197ee.json
export GOOGLE_APPLICATION_CREDENTIALS="/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
rm /home/ec2-user/google-credentials/photo-to-listing-113c764197ee.json
python3 photo_processing.py
cd /home/ec2-user/google-credentials/
ls -l
pwd
git pull origin master
image_file_path = '/home/ec2-user/DSC02674.jpg'
git pull origin master
python3 test-vision-api.py
cat test-vision-api
python3 test-vision-api
git pull origin master
pyton3 photo_processing.py
python3 photo_processing.py
python3 photo_processing.py
echo $GOOGLE_APPLICATION_CREDENTIALS
export GOOGLE_APPLICATION_CREDENTIALS="/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
echo $GOOGLE_APPLICATION_CREDENTIALS
python3 photo_processing.py
nano vision_test.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 Create test-single-image.py
python3 test-single-image.py
ls
python3 test-single-image
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
pip3 install Pillow
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
photo_processing.py
git pull origin master 
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
echo $GOOGLE_APPLICATION_CREDENTIALS
export GOOGLE_APPLICATION_CREDENTIALS="/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
echo $GOOGLE_APPLICATION_CREDENTIALS
nano /home/ec2-user/google-credentials/photo-to-listing-e89218601911.json
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull master
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
phthon3 photo_processing.py
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
git pull origin master
python3 photo_processing.py
python3 photo_processing.py
git pull origin masster
git pull origin master
python3 photo_processing.py
python3 photo_processing.py
pip install flask
git pull origin master
python3 app.py
git pull origin master
python3 app.py
curl http://127.0.0.1:5000/trigger-script
curl -X POST http://127.0.0.1:5000/trigger-script
git pull origin master
phyon3 app.py
python3 app.py
sudo lsof -i :5000
kill -9 388397
kill -9 388398
python3 app.py
source venv/bin/activate
python app.py
python3 app.py
python3 -m venv venv
source venv/bin/activate
pip install flask google-cloud-vision google-auth google-api-python-client pillow flask-cors
/home/ec2-user/venv/bin/python3 -m pip install --upgrade pip
cd /path/to/your/flask/app
pwd
ls
gunicorn --bind 0.0.0.0:5000 app:app
pip install gunicorn
gunicorn --version
gunicorn --bind 0.0.0.0:5000 app:app
gunicorn --bind 0.0.0.0:5000 app:app
source venv/bin/activate
gunicorn --version
gunicorn --bind 0.0.0.0:5000 app:app
sudo lsof -i :5000
kill -9 387669
kill -9 387670
sudo lsof -i :5000
gunicorn --bind 0.0.0.0:5000 app:app
curl -X POST http://127.0.0.1:5000/trigger-script
python3 app.py
ps aux | grep gunicorn
python3 app.py
curl -X POST http://127.0.0.1:5000/trigger-script
curl -X POST http://127.0.0.1:5000/run-photo-processing
source venv/bin/activate
gunicorn --bind 0.0.0.0:5000 app:app
sudo lsof -i :5000
pkill gunicorn
ps aux | grep gunicorn
sudo lsof -i :5000
crontab -l
sudo yum install cronie -y
crontab -l
gunicorn --bind 0.0.0.0:5000 app:app
sudo lsof -i :5000
gunicorn --bind 0.0.0.0:5000 app:app
source venv/bin/activate
which python
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 app:app
sudo lsof -i :5000
curl -X POST http://127.0.0.1:5000/run-photo-processing
curl -X POST http://127.0.0.1:5000/run-photo-processing
git pull origin master
pkill gunicorn  # If you are using Gunicorn
gunicorn --bind 0.0.0.0:5000 app:app
source venv/bin/activate
gunicorn --bind 0.0.0.0:5000 app:app
sudo lsof -i :5000
gunicorn --bind 0.0.0.0:5000 app:app
nano test_perplexity.py
python3 test_perplexity.py
ssh -i path_to_key.pem ec2-user@your-instance-ip
ssh -i ~/path_to_key.pem ec2-user@<EC2-Public-IP>
ssh: Could not resolve hostname your-instance-ip: Name or service not known
[ec2-user@ip-172-31-10-21 ~]$ ssh -i ~/path_to_key.pem ec2-user@<EC2-Public-IP>
-bash: syntax error near unexpected token `newline'
[ec2-user@ip-172-31-10-21 ~]$ 



[ec2-user@ip-172-31-10-21 ~]$ ssh -i ~/path_to_key.pem ec2-user@<EC2-Public-IP>
-bash: syntax error near unexpected token `newline'
[ec2-user@ip-172-31-10-21 ~]$ 


-bash: ssh:: command not found
-bash: syntax error near unexpected token `newline'
> 
[ec2-user@ip-172-31-10-21 ~]$ ssh -i ~/path_to_key.pem ec2-user@<EC2-Public-IP>
-bash: syntax error near unexpected token `newline'
[ec2-user@ip-172-31-10-21 ~]$ 


-bash: ssh:: command not found
-bash: syntax error near unexpected token `newline'
> 







exit

sudo lsof -i :5000
source venv/bin/activate
gunicorn --bind 0.0.0.0:5000 app:app
curl -X POST http://127.0.0.1:5000/run-photo-processing
python3 /home/ec2-user/photo_processing.py
git pull origin master
pkill gunicorn
gunicorn --bind 0.0.0.0:5000 --timeout 120 app:app
source venv/bin/activate
gunicorn --bind 0.0.0.0:5000 --timeout 120 app:app
source venv/bin/activate
ps aux | grep gunicorn
pwdx 2280
find ~ -name "*.log" -mtime -7
systemctl --user list-units --all
find ~ -name "*.pem"
ls ~/*.pem
ps aux | grep python
cat /home/ec2-user/app.py
git pull origin master
ps aux | grep gunicorn
kill -HUP 2280
ps aux | grep gunicorn
curl http://localhost:5000/
curl -X POST http://localhost:5000/trigger-script
curl -X POST http://localhost:5000/run-photo-processing
sudo tail -f /var/log/syslog | grep python
ls -l /home/ec2-user/*.log
ls -l *.log
ls -l ~/venv
source ~/venv/bin/activate
python --version
which python
find ~ -name app.py
cat /home/ec2-user/app.py
ps aux | grep gunicorn
ls -l ~/*.log
sudo find /etc/systemd/system -name "*flask*.service"
sudo find /etc/systemd/system -name "*gunicorn*.service"
ls -l /home/ec2-user/app.py
ls -l /home/ec2-user/photo_processing.py
ps aux | grep gunicorn | grep -v grep
sudo journalctl -u gunicorn
sudo journalctl | grep gunicorn
ls -l /etc/supervisor/conf.d/
find ~ -name "*.log" -mtime -7
ps -ef | grep gunicorn | grep -v grep
screen -ls
tmux ls
find ~ -name "*.log" -mtime -7
sudo tail -n 100 /var/log/messages | grep gunicorn
sudo journalctl | grep python
cat /etc/rc.local
ls -l /etc/systemd/system/multi-user.target.wants/
crontab -l
source venv/bin/activate
find ~ -name "*.service"
cat ~/.bashrc
ls -la ~/.bashrc.d
history | grep -i "gunicorn\|flask"
ps -fp 2280
ps aux | grep gunicorn
cat /proc/2280/environ | tr '\0' '\n'
screen -ls
tmux ls
id ec2-user
which gunicorn
sudo nano /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
source ~/venv/bin/activate
sudo journalctl -u gunicorn.service -n 50
source ~/venv/bin/activate
python3 -c "import sys; print(hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))"
which gunicorn
sudo cat /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
source ~/venv/bin/activate
sudo journalctl -u gunicorn.service -n 100 --no-pager
sudo lsof -i :5000
sudo kill 2280 15512
sudo lsof -i :5000
sudo systemctl start gunicorn
sudo systemctl status gunicorn
source ~/venv/bin/activate
python3 -c "import sys; print(hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))"
which gunicorn
sudo systemctl status gunicorn
source ~/venv/bin/activate
sudo systemctl enable gunicorn
curl http://localhost:5000
node -v
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
nvm --version
nvm install --lts
node -v
npm -v
mkdir product-listing-generator
cd product-listing-generator
npm init -y
npm install express openai dotenv
touch server.js
nano server.js
nano env
npm install
nano servr.js
node server.js
nano server.js
npm install express dotenv openai
node server.js
nano .env
ls -la
cat .env
rm env servr.js
node server.js
cd product-listing-generator
ls -la
node server.js
curl -X POST http://15.161.150.190:3000/generate-listing -H "Content-Type: application/json" -d '{"brand":"GUCCI","productCategory":"Women'\''s shoes","styleNumber":"GX3378","templateType":"shoes"}'
node server.js
lsof -i :3000
kill 32845
node server.js
cd product-listing-generator
node server.js
netstat -tuln | grep 3000
cd product-listing-generator
node server.js
netstat -tuln | grep 3000
node app.js
pwd
ls -l
curl -X POST http://15.161.150.190:3000/generate-listing -H "Content-Type: application/json" -d '{"prompt": "This is a test prompt"}'
curl -X POST http://localhost:3000/generate-listing -H "Content-Type: application/json" -d '{"brand":"GUCCI","productCategory":"Women'\''s shoes","styleNumber":"GX3378","templateType":"shoes"}'
sudo netstat -tuln | grep 3000
ps aux | grep node
node app.js
which node
echo $PATH
CD ~/.nvm/versions/node/v20.17.0/bin/node
cd ~/.nvm/versions/node/v20.17.0/bin/node
~/.nvm/versions/node/v20.17.0/bin/node /path/to/your/application/app.js
ls ~
cd ~/product-listing-generator
ls
~/.nvm/versions/node/v20.17.0/bin/node ~/product-listing-generator/server.js
cd ~/product-listing-generator
ls -al
ps aux | grep node
sudo kill -9 54540
~/.nvm/versions/node/v20.17.0/bin/node server.js
sudo netstat -tuln | grep 3000
nano server.js
nano ~/product-listing-generator/server.js
~/.nvm/versions/node/v20.17.0/bin/node ~/product-listing-generator/server.js
sudo lsof -i :3000
sudo kill -9 <53917>
sudo kill -9 53917
~/.nvm/versions/node/v20.17.0/bin/node ~/product-listing-generator/server.js
sudo tail -f /path/to/your/log/file.log
sudo ls /var/log
sudo tail -f /var/log/cloud-init-output.log
nano server.js
cd ~/product-listing-generator
nano server.js
export OPENAI_API_KEY="sk-0ZmM3wMLzmOd-hQcAmOlNphK3IbpalKQseu4eebvlDT3BlbkFJ3mDX_5R4gT2cSXNCRdndUgr5WOcVeadTkyqKDl9zgA"
source ~/.bashrc
import os
openai.api_key = os.getenv('OPENAI_API_KEY')
git pull origin master
python3 app.py
sudo lsof -i :5000
sudo kill -9 25108 25109 25110 25111
python3 app.py
sudo lsof -i :5000
python3 app.py
echo $OPENAI_API_KEY
import os
openai_api_key = os.getenv('OPENAI_API_KEY')
git pull origin master
ps aux | grep gunicorn
kill -9 89772 89773 89774 89775 89776
nohup gunicorn -w 4 -b 0.0.0.0:5000 app:app &
sudo lsof -i :5000
curl http://localhost:5000
sudo lsof -i :5000
git pull origin master
python3 app.py
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
sudo lsof -i :5000
sudo kill -9 88413
gunicorn -w 4 -b 0.0.0.0:5000 app:app
export OPENAI_API_KEY=sk-0ZmM3wMLzmOd-hQcAmOlNphK3IbpalKQseu4eebvlDT3BlbkFJ3mDX_5R4gT2cSXNCRdndUgr5WOcVeadTkyqKDl9zgA
gunicorn -w 4 -b 0.0.0.0:5000 app:app
sudo lsof -i :5000
sudo kill -9 89369 89370 89371 89372 89373
nohup gunicorn -w 4 -b 0.0.0.0:5000 app:app &
sudo lsof -i :5000
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
import openai
import os
# Set OpenAI API key
openai.api_key = 'sk-0ZmM3wMLzmOd-hQcAmOlNphK3IbpalKQseu4eebvlDT3BlbkFJ3mDX_5R4gT2cSXNCRdndUgr5WOcVeadTkyqKDl9zgA'
# Define the prompt
prompt = """
You are an eBay fashion product listing expert. Use the following details for the listing:
Brand: "RENE CAOVILLA"
Product Category: "Women's Shoes"
Product Type: "shoes"
Style Number: "CT1817-105-RV05Y063"

Information Retrieval
Please search for the product's information using the brand's official website as the primary source. If the required information is not available on the official website, use the following websites as secondary sources:
1. Net-A-Porter
2. Mytheresa
3. Flannels
4. Moda Operandi
If you still cannot find the required information, use other reliable fashion retail websites or sources. If any mandatory field information is unavailable after all attempts, indicate "N/A".

Fashion Product Listing Part 1: Mandatory and Optional Fields

Mandatory Fields:
1. Object Category (Categoria Oggetto) 
2. Store Category (Categoria del Negozio)
3. Brand (Marca) 
4. Size (Numero di scarpa EU) 
5. Department (Reparto) 
6. Color (Colore) 
7. Type (Tipo) 
8. Style (Stile) 
9. Condition of the Item (Condizione dell'oggetto) 
10. Price (Prezzo) 
11. Shipping Rule (Regola sulla spedizione)
Optional Fields:
1. MPN (MPN) 
2. Custom Label (Etichetta personalizzata - SKU) 
3. EAN (EAN) 
4. Material (Materiale della tomaia) 
5. Sole Material (Materiale della suola) 
6. Lining Material (Materiale della fodera)
"""

# Use ChatCompletion API in the latest OpenAI Python library
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",  # You can also use "gpt-4" depending on your subscription
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=500,
    temperature=0.7
)

# Print the response
print("Response:")
print(response['choices'][0]['message']['content'].strip())



curl -X POST http://<your-ec2-public-ip>:5000/generate-listing -H "Content-Type: application/json" -d '{"prompt": "Test listing generation"}'
curl -X POST http://15.161.150.190:5000/generate-listing -H "Content-Type: application/json" -d '{"prompt": "Test listing generation"}'
git pull origin master
python3 test_openai.py
python3 openaiexample.py
pip install openai
git pull origin master
test_openai.py
python3 test_openai.py
pip install --upgrade openai
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
pip install --upgrade openai
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
pip show openai
git pull origin master
python3 openaiexample.py
pip show openai
git pull origin master
python3 openaiexample.py
export OPENAI_API_KEY="sk-0ZmM3wMLzmOd-hQcAmOlNphK3IbpalKQseu4eebvlDT3BlbkFJ3mDX_5R4gT2cSXNCRdndUgr5WOcVeadTkyqKDl9zgA"
pkill gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
pip uninstall openai
pip install openai==0.28.0
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
git pull origin master
python3 test_openai.py
pip install openai
git pull origin master
python3 openaiexample.py
git pull origin master
python3 openaiexample.py
git pull origin master
python3 test_openai.py
git pull origin master
python3 openaiexample.py
git pull origin master
phyton3 openaiexample.py
python3 openaiexample.py
it pull origin master
git pull origin master
python3 perplexity.py
curl -X POST http://localhost:5001/generate-perplexity-listing -H "Content-Type: application/json" -d '{
  "brand": "BALENCIAGA",
  "styleNumber": "54236 W2FS8 4200",
  "productCategory": "Shoes"
}'
sudo lsof -i :5001
ls ~
python3 perplexity.py
ls ~/google-credentials
git pull origin master
Python3 perplexity.py
python3 perplexity.py
git pull origin master
python3 app.py
sudo lsof -i :5000
sudo kill -9 102958 102960 102961 102965 102975
python3 app.py
pyton3 test_perplexity.py
python3 test_perplexity.py
python3 test_perplexity.py.save
curl -X POST http://localhost:5001/generate-perplexity-listing -H "Content-Type: application/json" -d '{
  "brand": "BALENCIAGA",
  "styleNumber": "54236 W2FS8 4200",
  "productCategory": "Shoes"
}'
git pull origin master
python3 perplexity.py
git pull origin master
python3 perplexity.py
sudo lsof -i :5001
curl -X POST http://localhost:5001/generate-perplexity-listing -H "Content-Type: application/json" -d '{
  "brand": "BALENCIAGA",
  "styleNumber": "54236 W2FS8 4200",
  "productCategory": "Shoes"
}'
curl -X POST http://localhost:5001/generate-perplexity-listing -H "Content-Type: application/json" -d '{
  "brand": "BALENCIAGA",
  "styleNumber": "54236 W2FS8 4200",
  "productCategory": "Shoes"
}'
curl -X POST http://localhost:5001/generate-perplexity-listing -H "Content-Type: application/json" -d '{
  "brand": "BALENCIAGA",
  "styleNumber": "54236 W2FS8 4200",
  "productCategory": "Shoes"
}'
sudo lsof -i :5001
curl -X POST http://localhost:5001/generate-perplexity-listing -H "Content-Type: application/json" -d '{
  "brand": "BALENCIAGA",
  "styleNumber": "54236 W2FS8 4200",
  "productCategory": "Shoes"
}'
nano perplexity.py
git pull origin master
python3 perplexity.py
[ec2-user@ip-172-31-10-21 ~]$ python3 perplexity.py
 * Serving Flask app 'perplexity'
 * Debug mode: off
Address already in use
Port 5001 is in use by another program. Either identify and stop that program, or start the server with a different port.
[ec2-user@ip-172-31-10-21 ~]$ 
[ec2-user@ip-172-31-10-21 ~]$ python3 perplexity.py
 * Serving Flask app 'perplexity'
 * Debug mode: off
Address already in use
Port 5001 is in use by another program. Either identify and stop that program, or start the server with a different port.
[ec2-user@ip-172-31-10-21 ~]$
sudo lsof -i :5001
sudo kill -9 106999
python3 perplexity.py
curl -X POST http://15.161.150.190:5001/generate-perplexity-listing -H "Content-Type: application/json" -d '{
  "brand": "BALENCIAGA",
  "styleNumber": "54236 W2FS8 4200",
  "productCategory": "Shoes"
}'
const url = "http://15.161.150.190:5001/generate-perplexity-listing";
nano server.js
pwd
/home/ec2-user
ps aux | grep node
ps aux | grep flask
ls -al
cd ~/product-listing-generator
ls -al
nano server.js
pkill node
node server.js
nano server.js
npm install express body-parser axios
nano server.js
y
node server.js
ps aux | grep python
python3 app.py
python3 test_openai.py
git pull origin master
python3 prompt_testing_openai
git pull origin master
python3 prompt_testing_openai
git pull origin master
python3 prompt_testing_openai
import os
print(os.getenv('OPENAI_API_KEY'))
echo $SHELL
nano ~/.bash_profile
source ~/.bash_profile
echo $OPENAI_API_KEY
python3
ps aux | grep python
python3 app.py
git pull origin master
python3 app.py
ps aux | grep python
git pull origin master
python3 prompt_testing_openai
git pull origin master
python3 prompt_testing_openai
git pull origin master
python3 prompt_testing_openai
git pull origin master
python3 app.py
git pull origin master
python3 app.py
nano app.py
git pull origin master
ps aux | grep python
ps aux | grep pm2
ps aux | grep systemd
ps aux | grep supervisor
ps aux | grep python3
kill 183019
ps aux | grep python3
kill 183144
ps aux | grep app.py
kill 183207
python3 app.py
git pull origin master
python3 app.py
git pull origin master
python3 app.py
git pull origin master
python3 app.py
ps aux | grep python
python3 app.py
pip3 install Scrapy
scrapy startproject vestiaire_project
cd vestiaire_project
scrapy genspider vestiaire_spider us.vestiairecollective.com
git pull origin master
git pull origin master
