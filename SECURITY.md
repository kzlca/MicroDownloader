# Security policy

## Supported versions

The latest GitHub release is the supported series after it has been built and tested. Early releases may have bugs; do not use them as a substitute for backups.

## Private vulnerability reports

Please use [GitHub's private vulnerability reporting](https://github.com/kzlca/MicroDownloader/security/advisories/new) if the repository's Security tab offers it. If that option is not enabled, open an issue **without exploit details or secrets** to request a private contact method.

## Recovery and privacy limitations

- The application only repairs sparse/unallocated regions it can identify; filesystem allocation is **not a cryptographic integrity guarantee**.
- Repairs modify the selected local file; back up irreplaceable files first.
- Source download URLs are stored locally in SQLite in plaintext. Avoid storing signed URLs or login tokens.
- aria2 JSON-RPC is intended to bind only to loopback, with a random secret; do not expose it to the public network.
- Archive passwords may be passed to an external 7-Zip process and can briefly be visible in process arguments.
- Packaged binaries are not code-signed by default. Verify official release checksums and download only from the repository release page.
