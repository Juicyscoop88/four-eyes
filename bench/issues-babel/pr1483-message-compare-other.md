# Comparing a Message with None raises AttributeError

```python
from babel.messages.catalog import Message
Message('foo') == None   # AttributeError: 'NoneType' object has no attribute 'id'
```

Comparing a message with anything that is not a message fails the same way. It also breaks tools that inspect
a catalog generically (for example `dill.detect.baditems(read_po(...))`, as reported in Sphinx).
