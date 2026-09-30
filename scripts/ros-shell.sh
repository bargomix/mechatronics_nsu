#!/usr/bin/env bash
set -euo pipefail
exec docker exec -it mechatronics-pr01 bash --rcfile /work/scripts/ros.bashrc -i
