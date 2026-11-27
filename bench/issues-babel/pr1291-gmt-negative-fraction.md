# get_timezone_gmt shows the wrong hour for Newfoundland

```python
tz = get_timezone('America/St_Johns')          # UTC-03:30
dt = datetime(2007, 1, 1, 12, 0, tzinfo=tz)
get_timezone_gmt(dt, locale='en')              # 'GMT-04:30', expected 'GMT-03:30'
get_timezone_gmt(dt, 'short', locale='en')     # '-0430', expected '-0330'
```

`Pacific/Marquesas` (UTC-09:30) shows as `GMT-10:30`. India (`+05:30`) and Los Angeles (`-08:00`) are correct.
