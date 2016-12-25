#!/bin/bash

ret=0

find . -name '*_test.py' -print0 | xargs -0 -n1 python
[ $? -ne 0 ] && ret=1

LANGS=$(python -c 'import config; print " ".join(config.LANG_CODES_TO_LANG_NAMES)')
for l in $LANGS; do
    # I'm too lazy to write tests for most of the scripts,
    # and they usually break very obviously on Tools Labs anyway,
    # so just try importing them to do a quick syntax check
    for s in scripts/*.py; do
        echo "import-checking $s with CH_LANG=$l..."
        importable="$(echo "$s" | sed -E 's!scripts/(.*)\.py!\1!')"
        CH_LANG=$l PYTHONPATH=$PWD/scripts/ python -c "import $importable" && rm "${s}c"
        [ $? -ne 0 ] && ret=1
    done
done

exit $ret
