# The JavaScript extractor reports different line numbers on Windows line endings

Extracting messages from the same JavaScript file gives different line numbers depending on the line endings.
A call after three comment lines is reported on line 4 when the file uses LF, but on line 7 when it uses CRLF.
Our Windows colleagues get different references than Linux users, which causes noisy diffs in our catalogs.
The line numbers should be the same for LF and CRLF files.
