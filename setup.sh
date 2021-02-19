echo 1. Resizing EBS volume
sh resize.sh 50

echo 2. Installing prereqs
sudo pip3 install -r requirements.txt

echo 3. Bootstrapping CDK
cdk bootstrap --profile default

echo Deploying Faropt (enter 'y' at the prompt)
cdk deploy --profile default
