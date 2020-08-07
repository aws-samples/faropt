import os

# print('installing faropt')
# os.system('pip install -e .')

print('start test')
from faropt import *

print('[test] wrong framework init')
FarOpt('asd')

print('[test] missing stackname')
FarOpt('ortools','faroptmissing')