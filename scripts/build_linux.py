"""Build a portable Linux release on Linux; common checks live in build_portable."""

import sys

if __package__:
    from .build_portable import check_launch, check_archive, main
else:
    from build_portable import check_launch, check_archive, main


if __name__ == "__main__":
    if not sys.platform.startswith("linux"):
        raise SystemExit("Run this builder on Linux; cross-compilation is not supported.")
    raise SystemExit(main())
