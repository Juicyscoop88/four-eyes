# naturaltime and precisedelta raise OverflowError for far-future dates

`naturaltime(datetime(9999, 12, 31))` raises `OverflowError` instead of describing the date. `precisedelta` fails
the same way for such a date.
