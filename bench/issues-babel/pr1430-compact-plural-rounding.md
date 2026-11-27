# Compact decimal plural forms use the value before rounding

The long compact format picks the wrong word form for ordinary numbers:

```python
for locale, value in [('ru', 1100), ('pl', 1900), ('cs', 1100), ('fr', 1900)]:
    print(locale, format_compact_decimal(value, format_type='long', fraction_digits=0, locale=locale))
```

Actual:

```
ru 1 тысячи
pl 2 tysiąca
cs 1 tisíce
fr 2 millier
```

Expected:

```
ru 1 тысяча
pl 2 tysiące
cs 1 tisíc
fr 2 mille
```
