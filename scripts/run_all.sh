#!/bin/bash

SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"
RUN_DIR="${SCRIPT_DIR}/../runs"
TEST_SCRIPT="${SCRIPT_DIR}/vivado_yosys.sh"
STATIC_TEST_ARGS="-s 100"
BENCHMARK_DIR=  # $(readlink -f "${1:-vtr/verilog}")
BATCH_SIZE=6 # Runs 6x3 jobs in parallel (one for each synth method)

while [ "$1" != "" ]; do
  case $1 in
    -o | --output )         shift
                            RUN_DIR="$(realpath "$1")"
                            ;;
    -i | --input )          shift
                            BENCHMARK_DIR="$(realpath "$1")"
                            ;;
    -j | --batch_size)      shift
                            BATCH_SIZE="$1"
                            ;;
    * )                     echo "computer says no: ${1}"
                            exit 1
  esac
  shift
done

if [ -z "${RUN_DIR}" ]; then
  echo "Output directory must be specified!"
  exit 2
fi

# TODO(aryap): It'd be nice to be able to handle a list of sources, or any
# expansion.
if [ -d "${BENCHMARK_DIR}" ]; then
  benchmarks=(${BENCHMARK_DIR}/*.{v,vhdl,gz})
  num_benchmarks=${#benchmarks[@]}
elif [ -f "${BENCHMARK_DIR}" ]; then
  # Input is just one file
  benchmarks="${BENCHMARK_DIR}"
  num_benchmarks=1
else
  echo "Unsuitable input source: ${BENCHMARK_DIR}"
  exit 3
fi
echo "Input is ${BENCHMARK_DIR}: ${#benchmarks[@]} files"
echo "Output is: ${RUN_DIR}"

if ! [ -d "${RUN_DIR}" ]; then
  mkdir -p "${RUN_DIR}"
fi

pushd ${RUN_DIR}

i=0
pids=()

# Dispatch ${BATCH_SIZE}-many jobs in parallel and wait for them to complete,
# then continue, until all jobs are complete.
while [ ${i} -lt ${num_benchmarks} ]; do
  for ((j=0;j<${BATCH_SIZE} && i < ${num_benchmarks};j++)); do
    for method in vivado yosys yosys-abc9; do
      echo ${TEST_SCRIPT} -i ${benchmarks[i]} ${STATIC_TEST_ARGS} -m ${method}
      ${TEST_SCRIPT} -i ${benchmarks[i]} ${STATIC_TEST_ARGS} -m ${method} &
    done
    pids[${j}]=$!
    let "i=i+1"
  done
  echo "Dispatched ${#pids[@]} jobs"
  for pid in ${pids[*]}; do
    wait ${pid}
  done
  unset pids
done

popd
