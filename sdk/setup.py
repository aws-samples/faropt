import os
from glob import glob
import sys

from setuptools import setup, find_packages


def read(fname):
    """
    Args:
        fname:
    """
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

extras = {
    'async':[
        'scikit-optimize']
}


setup(name='faropt',
      version='0.2.20',
      description='Fargate based Numerical Optimization Template',
      url='https://github.com/aws-samples/faropt',
      author='Shreyas Subramanian',
      author_email='subshrey@amazon.com',
      license='MIT',
      packages=['faropt'],
      extras_require = extras,
      install_requires=["boto3"],
      zip_safe=False,
      classifiers=['Development Status :: 3 - Alpha',
                   "Intended Audience :: Developers",
                   "Natural Language :: English",
                   "License :: OSI Approved :: Apache Software License",
                   "Programming Language :: Python"],
      package_dir={'faropt': 'faropt/data/'},
      package_data={'faropt': ['data/routing/main.py']},
      long_description=read("README.rst")
      
     )
