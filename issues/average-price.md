# Average fill price on the order

Risk and client reporting both compute the average fill price themselves and they disagree on rounding.
Give the order one place that says it: the volume-weighted average price of its fills, none if it has no
fills yet. Report it to 6 decimal places, rounding half to even.
