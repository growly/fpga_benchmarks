#!/bin/bash

SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"
RUN_DIR="${SCRIPT_DIR}/../runs"
TEST_SCRIPT="${SCRIPT_DIR}/vivado_yosys.sh"
STATIC_TEST_ARGS="-s 30000"
BENCHMARK_DIR=  # $(readlink -f "${1:-vtr/verilog}")
BATCH_SIZE=8 # Will run 3x as many jobs as this at once
USE_LSF=false
DEVICE="xc7a200"

# NOTE(aryap): 'realpath' is a nice tool to do 'readlink -f' which is itself a
# nice too to recursively expand symlinks, but it isn't available on BWRC
# servers, and we have a more portable solution so I'm not installing it.

while [ "$1" != "" ]; do
  case $1 in
    -o | --output )         shift
                            RUN_DIR="$(readlink -f "$1")"
                            ;;
    -i | --input )          shift
                            BENCHMARK_DIR="$(readlink -f "$1")"
                            ;;
    -j | --batch_size)      shift
                            BATCH_SIZE="$1"
                            ;;
    -l | --lsf)             shift
                            USE_LSF=true
                            ;;
    -d | --device )         shift
                            DEVICE="$1"
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

LSF_PREFIX=
LSF_PREFIX_LOG=
LSF_MEMORY_LIMIT_KB=$((192*1024))  # 192 GB, our default unit is apparently MB
LSF_SWAP_LIMIT_KB=$((50*1024)) # 50 GB
if [ ${USE_LSF} = true ]; then
  # -K prefix should make this behave as any subprocess; we block until the job
  # completes and return when it does. So bash can background the job as per
  # usual.
  LSF_PREFIX="bsub -K -q normal -M ${LSF_MEMORY_LIMIT_KB} -v ${LSF_SWAP_LIMIT_KB}"
fi

# Dispatch ${BATCH_SIZE}-many jobs in parallel and wait for them to complete,
# then continue, until all jobs are complete.
while [ ${i} -lt ${num_benchmarks} ]; do
  for ((j=0;j<${BATCH_SIZE} && i < ${num_benchmarks};j++)); do
    for method in vivado yosys yosys-abc9; do
      if [ -n "${LSF_PREFIX}" ]; then
        # Add a meaningful log file to the LSF command if it's being used.
        LSF_PREFIX_LOG="-o bsub_${method}_$(basename ${benchmarks[i]}).log"
      fi
      echo ${LSF_PREFIX} ${LSF_PREFIX_LOG} ${TEST_SCRIPT} -i ${benchmarks[i]} ${STATIC_TEST_ARGS} -m ${method} -d ${DEVICE}
      ${LSF_PREFIX} ${LSF_PREFIX_LOG} ${TEST_SCRIPT} -i ${benchmarks[i]} ${STATIC_TEST_ARGS} -m ${method} -d ${DEVICE} &
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
