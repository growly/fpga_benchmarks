#!/bin/bash

SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"
RUN_DIR="${SCRIPT_DIR}/../runs"
TEST_SCRIPT="${SCRIPT_DIR}/vivado_yosys.sh"
STATIC_TEST_ARGS="-s 100"
BENCHMARK_DIR=$(readlink -f "${1:-vtr/verilog}")

pushd ${RUN_DIR}
i=0
for f in ${BENCHMARK_DIR}/*.v; do
  for method in vivado yosys yosys-abc9; do
    ${TEST_SCRIPT} -i ${f} ${STATIC_TEST_ARGS} -y ${method} &
    pids[${i}]=$!
    let "i=i+1"
  done
done
popd

echo "Started ${i} jobs"

for pid in ${pids[*]}; do
  wait ${pid}
done
