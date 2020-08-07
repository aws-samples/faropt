import boto3
import logging

class FarOpt(object):
    def __init__(self, framework = 'ortools', stackname = 'faropt'):
        
        # Check if backend stack is launched
        cf = boto3.client('cloudformation')
        try:
            response = cf.describe_stacks(StackName=stackname)
            if response['Stacks'][0]['StackStatus'] in ['CREATE_COMPLETE','UPDATE_COMPLETE']:
                print('FarOpt backend is ready!')
                self.ready = True
                self.stackname = stackname
                self.bucket = response['Stacks'][0]['Outputs'][0]['OutputValue']
        except Exception as e:
            self.ready = False
            print(e)
        
        self.allowed_frameworks = ['ortools']
        
        if framework not in self.allowed_frameworks:
            logging.warning("Only ortools is supported for now. You entered "+framework)
            #exit(0)
        else:
            self.framework = framework
    
    def configure (self):
        print("Configuring job")
        
    def submit(self):
        print("Submitting job")
        
    def logs(self):
        print("Tailing logs")