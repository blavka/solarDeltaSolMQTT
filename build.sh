#!/bin/sh
# Build source and wheel distributions from pyproject.toml.
set -eu

if [ "$(id -u)" -eq 0 ] && [ "${ALLOW_ROOT:-}" != 'yes' ]; then
    printf '%s\n' 'ERROR: Do not run this script as root!' >&2
    exit 2
fi

rm -rf build dist solarDeltaSolMQTT.egg-info

if command -v uv >/dev/null 2>&1; then
    uv build
else
    python3 -m build
fi
