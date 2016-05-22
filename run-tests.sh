#!/bin/bash

find . -name '*_test.py' -print0 | xargs -0 -n1 python

# I'm too lazy to write tests for most of the scripts,
# and they usually break very obviously on Tools Labs anyway,
# so just try importing them to do a quick syntax check
for s in scripts/*.py; do
    echo "import-checking $s..."
    importable="$(echo "$s" | sed -E 's!scripts/(.*)\.py!\1!')"
    CH_LANG=en PYTHONPATH=$PWD/scripts/ python -c "import $importable" && rm "${s}c"
done
