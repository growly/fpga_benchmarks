#!/bin/bash

SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"
RUN_DIR="${SCRIPT_DIR}/../runs"
TEST_SCRIPT="${SCRIPT_DIR}/vivado_yosys.sh"
STATIC_TEST_ARGS="-s 100"
BENCHMARK_DIR=$(readlink -f "${1:-vtr/verilog}")
BATCH_SIZE=3 # Runs 3x3 jobs in parallel (one for each synth method)

benchmarks=(${BENCHMARK_DIR}/*.v)
num_benchmarks=${#benchmarks[@]}
echo "${BENCHMARK_DIR}: ${#benchmarks[@]} files"

pushd ${RUN_DIR}

i=0
pids=()

# Dispatch ${BATCH_SIZE}-many jobs in parallel and wait for them to complete,
# then continue, until all jobs are dispatched.
while [ ${i} -lt ${num_benchmarks} ]; do
  for ((j=0;j<${BATCH_SIZE} && i < ${num_benchmarks};j++)); do
    for method in vivado yosys yosys-abc9; do
      echo ${TEST_SCRIPT} -i ${benchmarks[i]} ${STATIC_TEST_ARGS} -m ${method}
      ${TEST_SCRIPT} -i ${benchmarks[i]} ${STATIC_TEST_ARGS} -m ${method} &
    done
    pids[${j}]=$!
    let "i=i+1"
  done
  echo "dispatched ${#pids[@]} jobs"
  for pid in ${pids[*]}; do
    wait ${pid}
  done
  unset pids
done

popd
