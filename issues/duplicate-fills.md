# Fills counted twice after a redelivery

Last week the venue gateway redelivered execution reports after a reconnect and some fills were applied
twice. Every execution report has an execution id from the venue. Applying the same execution twice must
not change the order a second time. Different executions of the same order are still all applied.
