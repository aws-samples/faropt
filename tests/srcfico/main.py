import xpress as xp


try:
    strg = ""
    print('Using Xpress from file: ' + xp.__file__)
    xp.beginlicensing()
    oemnum = 63112059
    n, strg = xp.license(0, strg)
    lic = oemnum - n * n // 19
    n, strg = xp.license(lic, strg)
    # The expected result for strg is "Xpress-MP licensed by Fair Isaac Corporation to Amazon Applications"
    print("License String: " + strg)
    xp.endlicensing()
except:
    raise RuntimeError("License not accepted!")

x1 = xp.var(vartype=xp.integer, name='x1', lb=-10, ub=10)
x2 = xp.var(name='x2')
p = xp.problem(x1, x2,x1**2 + 2*x2,x1 + 3*x2 >= 4,name='licensetest')  # problem name (optional)
p.solve()

print ("solution: {0} = {1}; {2} = {3}".format (x1.name, p.getSolution(x1), x2.name, p.getSolution(x2)))

