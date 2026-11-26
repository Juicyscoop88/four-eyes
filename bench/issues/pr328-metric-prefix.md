# metric shows 1000 V instead of 1.00 kV

metric can show a four digit number with a prefix that is too small:

```
metric(999.9, "V")     -> '1000 V'    expected '1.00 kV'
metric(999999, "V")    -> '1000 kV'   expected '1.00 MV'
metric(0.0009999, "V") -> '1000 μV'   expected '1.00 mV'
```

The docstring says the prefix is chosen so that 1,230,000 becomes 1.23M, not 1230K.
