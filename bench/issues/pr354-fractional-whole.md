# fractional prints 2 1/1 when the fraction rounds to a whole number

```
fractional(2.9999999) -> '2 1/1'   expected '3'
fractional(0.9999999) -> '1/1'     expected '1'
fractional(0)         -> '0/1'     expected '0'
```
