#!/bin/bash

SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"
RUN_DIR="${SCRIPT_DIR}/../runs"
TEST_SCRIPT="${SCRIPT_DIR}/vivado_yosys.sh"
STATIC_TEST_ARGS="-s 30000"
BENCHMARK_DIR=  # $(readlink -f "${1:-vtr/verilog}")
BATCH_SIZE=10 # Will run 3x as many jobs as this at once
USE_LSF=false
DEVICE="xc7a200"
SYNTH_METHODS="vivado yosys yosys-abc9"

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
    -l | --lsf)             USE_LSF=true
                            ;;
    -d | --device )         shift
                            DEVICE="$1"
                            ;;
    -m | --synth_method )   shift
                            SYNTH_METHODS="$1"
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

# FIXME(aryap): also in vivado_yosys.sh: .gz inputs must be expanded to
# .v/.vhdl and merged with the other inputs, and then sources de-duplicated.
# Could use sort/uniq? Or write the algorithm in bash (worse). Expanding .gz
# inputs must be removed from the vivado_yosys.sh script so it doesn't have to
# deal with with multiple runs clobbering the same test scripts.

# TODO(aryap): It'd be nice to be able to handle a list of sources, or any
# expansion.
if [ -d "${BENCHMARK_DIR}" ]; then
  # TODO(aryap): This is a dangerously-bash bashism
  shopt -s nullglob
  #benchmarks=( ${BENCHMARK_DIR}/*.{v,vhdl,gz} )
  benchmarks=( ${BENCHMARK_DIR}/*.{v,vhdl} )
  num_benchmarks=${#benchmarks[@]}
  echo "Found ${num_benchmarks} benchmarks:"
  for file in "${benchmarks[@]}"; do
    echo "  ${file}"
  done
  shopt -u nullglob
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

launch_job() {
  benchmark="$1"
  method="$2"
  if [ -n "${LSF_PREFIX}" ]; then
    # Add a meaningful log file to the LSF command if it's being used.
    LSF_PREFIX_LOG="-o bsub_${method}_$(basename ${benchmarks[i]}).log"
  fi
  echo ${LSF_PREFIX} ${LSF_PREFIX_LOG} ${TEST_SCRIPT} -i "${benchmark}" ${STATIC_TEST_ARGS} -m "${method}" -d ${DEVICE}
  ${LSF_PREFIX} ${LSF_PREFIX_LOG} ${TEST_SCRIPT} -i "${benchmark}" ${STATIC_TEST_ARGS} -m "${method}" -d ${DEVICE} &
}

# Dispatch ${BATCH_SIZE}-many jobs in parallel and wait for them to complete,
# then continue, until all jobs are complete.
batch_controlled_launch() {
  i=0
  while [ ${i} -lt ${num_benchmarks} ]; do
    for ((j=0;j<${BATCH_SIZE} && i < ${num_benchmarks};j++)); do
      for method in ${SYNTH_METHODS}; do
        launch_job "${benchmarks[i]}" "${method}" &
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
}

# Launch up to #{BATCH_SIZE}-many jobs. As soon as one terminates, launch the next.
# REQUIRES Bash 4.3.
# https://mywiki.wooledge.org/ProcessManagement#advanced
token_controlled_launch() {
  i=0
  tokens=0
  while [ ${i} -lt ${num_benchmarks} ]; do
    for ((j=0;j<${BATCH_SIZE} && i < ${num_benchmarks};j++)); do
      for method in ${SYNTH_METHODS}; do
        launch_job "${benchmarks[i]}" "${method}"
        if (( tokens++ >= BATCH_SIZE )); then
          wait -n
          let "tokens=tokens-1"
        fi
      done
      let "i=i+1"
    done
  done
}

token_controlled_launch

# Test is wait -n makes sense?
# Really to test if we're on bash >4.3. I mean, _really_ we want something portable.
# "All builtins return an exit status of 2 to indicate incorrect usage,
# generally invalid options or missing arguments."
# https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html
wait -n
return_value=$?
if (( return_value == 2 )); then
  echo "Using batch-controlled launch"
  batch_controlled_launch
else
  echo "Using token-controlled launch"
  token_controlled_launch
fi

popd
