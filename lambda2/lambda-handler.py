import json
import ortools
import subprocess
import os
import sys
import zipfile
import boto3
from black import format_str, FileMode, format_file_in_place
from pathlib import Path
import shutil

def main(event, context):
    
    print(" Starting LambdaOpt backend")
    print("\n███████╗ █████╗ ██████╗  ██████╗ ██████╗ ████████╗\n██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝\n█████╗  ███████║██████╔╝██║   ██║██████╔╝   ██║   \n██╔══╝  ██╔══██║██╔══██╗██║   ██║██╔═══╝    ██║   \n██║     ██║  ██║██║  ██║╚██████╔╝██║        ██║   \n╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝        ╚═╝   \n\n")
    print("---------------------------------------------------------------")
    print('Downloading source')
    
    print('Looking for source.zip in ',event['s3bucket'],'/',event['s3key']+'/source.zip')
    
    s3 = boto3.client('s3')
    try:
        s3.download_file(event['s3bucket'], event['s3key']+'/source.zip', '/tmp/source.zip')
        print('Downloaded source.zip! uncompressing')
    except:
        print('Could not download source. Please check :',event['s3bucket'],'/',event['s3key']+'/source.zip')
        
    print("Setting env variables for micro environment")
    os.environ['s3key'] = event['s3key']
    os.environ['s3bucket']= event['s3bucket']
    
    with zipfile.ZipFile('/tmp/source.zip', 'r') as zip_ref:
        zip_ref.extractall('/tmp/')
    

    print("---------------------------------------------------------------")
    
    # Add utils file

    f = open("/var/task/utils.py", 'r')
    utilsstr = f.read()
    f.close()
    
    # Rewrite to tmp
    f = open("/tmp/utils.py",'w')
    f.write(utilsstr)
    f.close()
    
    listfiles = os.listdir("/tmp/")
    print("reformatting with black")
    for f in listfiles:
        if f[-2:] == 'py':
            print(f)
            format_file_in_place(src=Path('/tmp/'+f), fast=True, mode=FileMode())  
    
    os.environ["PYTHONPATH"] = "/opt/python/lib/python3.7/site-packages"
    process = subprocess.Popen([sys.executable, "/tmp/main.py"], env = os.environ, stdin=subprocess.PIPE, stdout=subprocess.PIPE,  stderr=subprocess.STDOUT)
    output, error = process.communicate()
    
    print(output.decode())
    print("----")
    print(error)

    return {
        'statusCode': 200,
        'body': json.dumps({'error':error})
    }
