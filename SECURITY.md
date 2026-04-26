# Security

Report vulnerabilities privately via the GitHub Security tab on this
repository. Do not open a public issue for security problems.

We aim to acknowledge within 5 days and ship a fix within 30 days for
high-severity issues. The library executes no remote code paths, runs no
network operations, and parses LAS/LAZ files only via the upstream `laspy`
parser; most security risk lives at that layer.
