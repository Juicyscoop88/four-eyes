# intword shows 1000.0 sextillion for very large numbers

For very large numbers just below a power of a thousand, intword stays at the lower word:

```
intword(10**24 - 1) -> '1000.0 sextillion'   expected '1.0 septillion'
intword(10**27 - 1) -> '1000.0 septillion'   expected '1.0 octillion'
```

The same happens at 10**30 and 10**33. Smaller numbers carry over correctly.
