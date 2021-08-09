#!/bin/bash
# Job name:
#SBATCH --job-name=test_run
#
# Account:
#SBATCH --account=fc_bdmesh
#
# Partition:
#SBATCH --partition=savio	
#
# Quality of Service:
#SBATCH --qos=savio_normal
# Num Cores per Task
#SBATCH --cpus-per-task=4
#
# Wall clock limit:
#SBATCH --time=00:10:00
#
## Command(s) to run:
ip="lib2_or1200"
RESULTS_DIR="/global/home/users/minwoo_kang/fpga_benchmarks/run_$ip"
STATIC_TEST_ARGS="-s 5000"

benchmark="/global/"
./single_run_abc.sh -i $benchmark ${STATIC_TEST_ARGS} -m "${method}" -d ${DEVICE} -n ${seq_index} -r ${RANDOM_SEQ_LEN} -l ${LUT_LIB}

