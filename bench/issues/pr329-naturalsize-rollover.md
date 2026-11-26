# naturalsize shows 1000.0 kB instead of 1.0 MB

Just below a unit boundary the size is shown with the old unit:

```
naturalsize(999999)                     -> '1000.0 kB'   expected '1.0 MB'
naturalsize(999999999)                  -> '1000.0 MB'   expected '1.0 GB'
naturalsize(1024 ** 2 - 1, binary=True) -> '1024.0 KiB'  expected '1.0 MiB'
```

It happens at every decimal, binary and GNU boundary.
