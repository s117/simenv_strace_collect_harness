#!/bin/bash
set -e
RUN_ROOT_DIR=$1
if [ -d "$RUN_ROOT_DIR" ]; then
    echo "Launching all jobs in $RUN_ROOT_DIR"
fi

for p in "$RUN_ROOT_DIR"/*; do
    pushd "$p" || exit 255
    bsub < bsub_job.sh
    popd || exit 255
done