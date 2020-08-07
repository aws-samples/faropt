import boto3
import logging

class FarOpt(object):
    def __init__(self, uri, framework = 'ortools', stackname = 'faropt'):
        
        # Check if backend stack is launched
        cf = boto3.client('cloudformation')
        try:
            response = cf.describe_stack_set(StackSetName=stackname)
            if response['Stacks'][0]['StackStatus'] in ['CREATE_COMPLETE','UPDATE_COMPLETE']:
                print('FarOpt status ready!')
                self.ready = True
                self.stackname = stackname
        except Exception as e:
            self.ready = False
            print(e)
        
        
        self.uri = uri
        self.frameworks = ['ortools']
        
        if framework not in self.frameworks:
            logging.warning("Only ortools is supported for now. You entered "+framework)
            #exit(0)
        else:
            self.framework = framework