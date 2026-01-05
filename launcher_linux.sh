#!/bin/bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)
source "./venv/bin/activate"
python3.10 "src/init.py" >> ./fcs.log 2>&1 &
