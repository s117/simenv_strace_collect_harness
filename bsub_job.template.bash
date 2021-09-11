#!/bin/bash
#BSUB -n 1
#BSUB -W {time_limit}
#BSUB -R select[model==Gold6130]
#BSUB -R rusage[mem={memory_limit}]
#BSUB -o job-%J.stdout
#BSUB -e job-%J.stderr
#BSUB -J {job_name}
export PATH={riscv_bin_path}:$PATH
make run
