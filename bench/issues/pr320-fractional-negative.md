# fractional prints two minus signs for negative mixed numbers

`fractional(-1.3)` returns `'-1 -3/10'`, and `fractional(-2.5)` returns `'-2 -1/2'`. It happens for any negative
number whose absolute value is at least 1. Expected `'-1 3/10'` and `'-2 1/2'`.
