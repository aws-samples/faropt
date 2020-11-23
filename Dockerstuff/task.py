import boto3
import sys
import os

print(" Starting FarOpt backend")
print("\n███████╗ █████╗ ██████╗  ██████╗ ██████╗ ████████╗\n██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝\n█████╗  ███████║██████╔╝██║   ██║██████╔╝   ██║   \n██╔══╝  ██╔══██║██╔══██╗██║   ██║██╔═══╝    ██║   \n██║     ██║  ██║██║  ██║╚██████╔╝██║        ██║   \n╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝        ╚═╝   \n\n")
print("---------------------------------------------------------------")
print('Downloading source')

print('Looking for source.zip in ',os.environ['s3bucket'],'/',os.environ['s3key'])
print('Note:')
print('s3bucket : ', os.environ['s3bucket'])
print('s3key : ', os.environ['s3key'])


s3 = boto3.client('s3')
try:
    s3.download_file(os.environ['s3bucket'], os.environ['s3key']+'/source.zip', 'source.zip')
    print('Downloaded source.zip! uncompressing')
except:
    print('Could not download source. Please check :',os.environ['s3bucket'],'/',os.environ['s3key']+'/source.zip')
    


import zipfile
with zipfile.ZipFile('source.zip', 'r') as zip_ref:
    zip_ref.extractall('/tmp/')

listfiles = os.listdir("/tmp/")

print("---------------------------------------------------------------")
# print('Checking script with modulefinder...')
# from modulefinder import ModuleFinder

# finder = ModuleFinder()
# finder.run_script('/tmp/main.py') #This will also determine if there is no main function

# print('Loaded modules:')
# for name, mod in finder.modules.items():
#     print('%s: ' % name, end='')
#     print(','.join(list(mod.globalnames.keys())[:3]))

# print('-'*50)
# print('Modules not imported:')
# print('\n'.join(finder.badmodules.keys()))

import subprocess

print(listfiles)

sys.stdout.flush()

if 'main.jl' in listfiles:
    subprocess.run('julia /tmp/main.jl'.split(' '),stderr=sys.stderr, stdout=sys.stdout)
elif 'main.py' in listfiles:
    subprocess.run('python /tmp/main.py'.split(' '),stderr=sys.stderr, stdout=sys.stdout)
else:
    print('Please add a main script (main.py or main.jl) at the root of your project folder.')