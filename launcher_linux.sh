#!/bin/bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)
source "./venv/bin/activate"
python "src/init.py" > /dev/null 2>&1 &
