#!/bin/bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)
source "../venvs/venv/bin/activate"
python "scripts/init.py"
