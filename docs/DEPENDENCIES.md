# Dependencies

## Runtime

- Static demos: a current browser; no account, server, remote asset, or automatic network request. Public attribution links open only after a user action.
- Python tools and CLIs: Python 3.11 or 3.12 and the standard library.
- Native human-in-the-loop lab: Python's Tk binding and a graphical display; the headless core and tests do not require a display.
- Bulk price and migration mutation paths: POSIX advisory locks and filesystem semantics.

No project has a third-party runtime Python package dependency. ODbL/DbCL govern the bundled public database content; they are data terms, not runtime software dependencies.

## Verification only

Browser checks use Playwright 1.62.0 with its matching Firefox bundle. `requirements-ci.lock` pins Playwright and Python transitive packages by exact version and SHA-256 for CPython 3.11/3.12 on x86-64 Linux. The browser bundle is installed explicitly; it is not a demo runtime dependency.

GitHub CI pins checkout and Python setup actions to reviewed full commit SHAs. Mutable action tags are comments only. Dependency upgrades require focused review, lock refresh, browser replay, and a clean-tree check.

Two projects declare package build backends used only when a reviewer builds distributions. Repository verification imports their source trees directly and does not require a package build.
