using JuMP  # Need to say it whenever we use JuMP

using GLPKMathProgInterface # Loading the GLPK module for using its solver


#MODEL CONSTRUCTION
#--------------------

myModel = Model(solver=GLPKSolverLP()) 
# Name of the model object. All constraints and variables of an optimization problem are associated 
# with a particular model object. The name of the model object does not have to be myModel, it can be yourModel too! The argument of Model,
# solver=GLPKsolverLP() means that to solve the optimization problem we will use GLPK solver.

#VARIABLES
#---------

# A variable is modelled using @defVar(name of the model object, variable name and bound, variable type)
# Bound can be lower bound, upper bound or both. If no variable type is defined, then it is treated as 
#real. For binary variable write Bin and for integer use Int.

@defVar(myModel, x >= 0) # Models x >=0

# Some possible variations:
# @defVar(myModel, x, Binary) # No bound on x present, but x is a binary variable now
# @defVar(myModel, x <= 10) # This one defines a variable with lower bound x <= 10
# @defVar(myModel, 0 <= x <= 10, Int) # This one has both lower and upper bound, and x is an integer

@defVar(myModel, y >= 0) # Models y >= 0

#OBJECTIVE
#---------

@setObjective(myModel, Min, x + y) # Sets the objective to be minimized. For maximization use Max

#CONSTRAINTS
#-----------

@addConstraint(myModel, x + y <= 1) # Adds the constraint x + y <= 1

#THE MODEL IN A HUMAN-READABLE FORMAT
#------------------------------------
println("The optimization problem to be solved is:")
print(myModel) # Shows the model constructed in a human-readable form

#SOLVE IT AND DISPLAY THE RESULTS
#--------------------------------
status = solve(myModel) # solves the model  

println("Objective value: ", getObjectiveValue(myModel)) # getObjectiveValue(model_name) gives the optimum objective value
println("x = ", getValue(x)) # getValue(decision_variable) will give the optimum value of the associated decision variable
println("y = ", getValue(y))