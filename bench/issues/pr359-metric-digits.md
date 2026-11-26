# metric shows one significant digit too many after rounding

With the default precision of 3, some values come out with four significant digits:

```
metric(9999)    -> '10.00 k'   (4 digits)
metric(99999)   -> '100.0 k'   (4 digits)
metric(9.99999) -> '10.00'
```

The neighbours are right: metric(10000) is '10.0 k' and metric(100000) is '100 k'.
