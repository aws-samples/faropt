import json

from faropt import FarOpt
from faropt.templates.routing import RoutingOpt
from faropt.templates.blackbox import AsyncOpt

fo = FarOpt()
ro = RoutingOpt()
ao = AsyncOpt()

def lambda_handler(event, context):
    # TODO implement
    
    if event['object']=='FarOpt':
        try:
            body = getattr(fo,event['method'])(**event['args'])
        except Exception as e:
            body = str(e)
        
    elif event['object']=='RoutingOpt':
        try:
            body = getattr(ro,event['method'])(**event['args'])
        except Exception as e:
            body = str(e)
            
    elif event['object']=='AsyncOpt':
        try:
            body = getattr(ao,event['method'])(**event['args'])
        except Exception as e:
            body = str(e)
        
    else:
        body = 'Call not supported!'
    
    return {
        'statusCode': 200,
        'body': json.dumps(body)
    }
