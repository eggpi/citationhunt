#!/bin/sh

find . -name '*_test.py' -print0 | xargs -0 -n1 python
