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
