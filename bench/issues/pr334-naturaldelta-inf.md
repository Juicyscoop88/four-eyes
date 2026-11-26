# naturaldelta raises OverflowError for infinity

The docstring says values that cannot be turned into a timedelta are returned unchanged, and
`naturaldelta(float("nan"))` returns `'nan'`. But `naturaldelta(float("inf"))` raises
`OverflowError: cannot convert float infinity to integer`. Expected `'inf'` (and `'-inf'` for minus infinity).
A finite value that is simply too large should still raise as documented.
