.. faropt documentation master file, created by
   sphinx-quickstart on Tue Nov 24 23:19:35 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to faropt's documentation!
==================================

.. toctree::
   :maxdepth: 4
   :caption: Contents:




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`




Using the SDK
=============

For a basic Walkthrough, do:
----------------------------

.. code-block:: python

   from faropt import FarOpt

   // init a FarOpt object
   fo = FarOpt()

   // point to your source code, with a main.py and any other files and/or subfolders
   fo.configure('../project/src/')

   // submit the job
   fo.submit()

   // print logs()
   fo.logs()


Saving and running a recipe
---------------------------

.. code-block:: python

	// add a recipe after submitting a job
	fo.add_recipe(recipe_name='routing-v1', maintainer='Dexter')

	// get unique recipe ID
	r_id = fo.get_recipe_id_from_description(description='routing-v1')

	// run this recipe
	fo.run_recipe(r_id)


For black box optimization problems:
------------------------------------
.. code-block:: python

	from faropt.templates.blackbox import AsyncOpt

	// init an AsyncOpt object
	ao = AsyncOpt()

	// list existing models
	ao.list_models()

	// create a new model 
	ao.create_model(bounds = [(-1.0,1.0), (-5.0,5.0), (-3,3)])], model_tag = 'engine1')

	// ask optimizer for a new point to evaluate
	ao.ask_model(modelname = ...)

	// tell the optimizer results of a evaluation
	ao.tell_model(xval = [0,0,1], fval = 0.5, modelname= ...s)



Example code
------------

See example code here - https://github.com/aws-samples/faropt/blob/master/tests/src/main.py


.. code-block:: python3

   """Capacited Vehicles Routing Problem (CVRP)."""

   # [START import]
   from __future__ import print_function
   from ortools.constraint_solver import routing_enums_pb2
   from ortools.constraint_solver import pywrapcp
   from utils import *
   # [END import]


   # [START data_model]
   def create_data_model():
       """Stores the data for the problem."""
       data = {}
       data['distance_matrix'] = [
           [
               0, 548, 776, 696, 582, 274, 502, 194, 308, 194, 536, 502, 388, 354,
               468, 776, 662
           ],

       //.
       //.
       //.
       //.
       //.

       # Solve the problem.
       # [START solve]
       solution = routing.SolveWithParameters(search_parameters)
       # [END solve]

       # Print solution on console.
       # [START print_solution]
       print('printing solutions')
       if solution:
           print_solution(data, manager, routing, solution)
       # [END print_solution]


   main()



Logs from the back end ...
--------------------------

.. code-block:: html

   1598041071123 |  Starting FarOpt backend
   1598041071123 | ███████╗ █████╗ ██████╗  ██████╗ ██████╗ ████████╗
   1598041071123 | ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝
   1598041071123 | █████╗  ███████║██████╔╝██║   ██║██████╔╝   ██║   
   1598041071123 | ██╔══╝  ██╔══██║██╔══██╗██║   ██║██╔═══╝    ██║   
   1598041071123 | ██║     ██║  ██║██║  ██║╚██████╔╝██║        ██║   
   1598041071123 | ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝        ╚═╝  
   .
   .
   .
   .
   .


Back-end architecture
=====================

Fargate based serverless Numerical Optimization
-----------------------------------------------


.. image:: ./FarOpt.png
   :target: ./FarOpt.png
   :alt: 


This architecture is a bare bones template of how you can run optimization models in a serverless fashion on Fargate. The Open source SDK can be used to submit optimization tasks and receive logs. 
Fargate will launch the container, run your code, push logs to cloudwatch and exit - you only pay for the seconds that this *optimzation task* runs. 

Currently supported frameworks inlcude: 


#. PuLP
#. Pyomo
#. OR Tools
#. JuMP (Julia)


What's coming up?
=================


#. Scheduling optimization jobs
#. Demand forecasting using Forecast
#. Quantum Approximate Optimization Algorithm
#. SageMaker RL solvers for certain problem types


How to use this CDK project
===========================

You should explore the contents of this project. It demonstrates a CDK app with an instance of a stack (\ ``faropt_stack``\ )
which contains an Amazon SQS queue that is subscribed to an Amazon SNS topic.

The ``cdk.json`` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization process also creates
a virtualenv within this project, stored under the .env directory.  To create the virtualenv
it assumes that there is a ``python3`` executable in your path with access to the ``venv`` package.
If for any reason the automatic creation of the virtualenv fails, you can create the virtualenv
manually once the init process completes.

To manually create a virtualenv on MacOS and Linux:

.. code-block:: html

   $ python3 -m venv .env

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

.. code-block:: html

   $ source .env/bin/activate

If you are a Windows platform, you would activate the virtualenv like this:

.. code-block:: html

   % .env\Scripts\activate.bat

Once the virtualenv is activated, you can install the required dependencies.

.. code-block:: html

   $ pip install -r requirements.txt

At this point you can now synthesize the CloudFormation template for this code.

.. code-block:: html

   $ cdk synth

You can now begin exploring the source code, contained in the hello directory.
There is also a very trivial test included that can be run like this:

.. code-block:: html

   $ pytest

To add additional dependencies, for example other CDK libraries, just add to
your requirements.txt file and rerun the ``pip install -r requirements.txt``
command.

Useful commands for the back end stack
--------------------------------------


* ``cdk ls``          list all stacks in the app
* ``cdk synth``       emits the synthesized CloudFormation template
* ``cdk deploy``      deploy this stack to your default AWS account/region
* ``cdk diff``        compare deployed stack with current state
* ``cdk docs``        open CDK documentation

Enjoy!
