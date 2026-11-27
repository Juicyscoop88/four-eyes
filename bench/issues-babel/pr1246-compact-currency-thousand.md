# format_compact_currency fails for exactly 1000 in Dutch

Formatting money in the compact format fails for exactly one thousand euros in the Dutch locale. A penny more
or less works:

```python
format_compact_currency(1000.01, 'EUR', locale='nl')   # '€ 1K'
format_compact_currency(1000, 'EUR', locale='nl')      # KeyError: '1000'
```

`nl_NL` and `nl_BE` fail the same way. Other locales may be affected too.
