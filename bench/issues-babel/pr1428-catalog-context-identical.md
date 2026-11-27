# Catalog.is_identical() is always False when the catalog has a message context

A catalog that contains a context-specific message is not identical even to itself:

```python
c = Catalog(locale='ja')
c.add('Guide', 'ガイド', context='navigation')
c.is_identical(c)   # False
```

Because `pybabel update --check` uses this, it reports every catalog that uses `pgettext` or `npgettext` as
out of date on every run, so we cannot use it as a check in CI.
