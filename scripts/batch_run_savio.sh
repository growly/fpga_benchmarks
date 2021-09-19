#!/bin/bash

SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"
RUN_DIR="${SCRIPT_DIR}/../runs"
TEST_SCRIPT="${SCRIPT_DIR}/single_run_yosys-abc.sh"
STATIC_TEST_ARGS="-s 5000"
BENCHMARK_DIR=  # $(readlink -f "${1:-vtr/verilog}")
BATCH_SIZE=8 # Actually spawns 3x this many jobs, one for each synth method (below)
USE_LSF=false
USE_SLURM=false
DEVICE="xc7a200"
# SYNTH_METHODS "yosys yosys-abc9"
SYNTH_METHODS="yosys-abc9"
LUT_LIB=0

RANDOM_SEQ_LEN=0
NUM_OPTS=9
PERMUTATIONS=$(( 1 * 3))


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
    -r | --random )         shift
                            RANDOM_SEQ_LEN=$1
                            ;;
    -j | --batch_size)      shift
                            BATCH_SIZE="$1"
                            ;;
    -b | --lut_lib)         shift
                            LUT_LIB="$1"
                            ;;
    -s | --slurm)           USE_SLURM=true
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

# Setup run output directory
if ! [ -d "${RUN_DIR}" ]; then
  mkdir -p "${RUN_DIR}"
fi

pushd ${RUN_DIR}


# Calculate which indices to run exhaustive search on
MIN_PASS_LENGTH=0
MIN_NUM_RUNS=$(( $PERMUTATIONS * (($NUM_OPTS**($MIN_PASS_LENGTH+1)-1) / ($NUM_OPTS-1) - 1) ))

MAX_PASS_LENGTH=4
MAX_NUM_RUNS=$(( $PERMUTATIONS * (($NUM_OPTS**($MAX_PASS_LENGTH+1)-1) / ($NUM_OPTS-1) - 1)  ))
echo $(( $MAX_NUM_RUNS - $MIN_NUM_RUNS ))

# IF USING RANDOM; set up min/max indices manually
if [ ${RANDOM_SEQ_LEN} -gt 0 ]; then
  MIN_NUM_RUNS=487
  MAX_NUM_RUNS=489
fi


# LSF config
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

# LAUNCH JOB-SLURM or LSF or Local
launch_job() {
  if [ ${USE_SLURM} = true ]; then
    launch_slurm_job $1 $2 $3 $4
  else
    launch_lsf_job $1 $2 $3 $4
  fi
}

# Launch Jobs with slurm (on Savio cluster)
launch_slurm_job() {
  pid_index=$1
  benchmark=$2
  method=$3
  seq_index=$4
  
  # Name of "IP" (current benchmark)
  verilog_file="$(basename -- $benchmark)"
  ip=${verilog_file%.*}
  if [ ${RANDOM_SEQ_LEN} -gt 0 ]; then
      slurm_script_name="${ip}_random_$3_max${RANDOM_SEQ_LEN}_$4"
  else
      slurm_script_name="${ip}_$3_$4"      
  fi

  echo $slurm_script_name
  cat > "${slurm_script_name}.sh" <<EOT
#!/bin/bash
# generated at $(date) by run_all.sh
# Job name:
#SBATCH --job-name=${slurm_script_name}
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
#SBATCH --time=01:00:00
#
## Command(s) to run:
echo ${TEST_SCRIPT} -i $benchmark ${STATIC_TEST_ARGS} -m "${method}" -d ${DEVICE} -n ${seq_index} -r ${RANDOM_SEQ_LEN} -l ${LUT_LIB}
${TEST_SCRIPT} -i $benchmark ${STATIC_TEST_ARGS} -m "${method}" -d ${DEVICE} -n ${seq_index} -r ${RANDOM_SEQ_LEN} -l ${LUT_LIB}
EOT
  # TODO: run slurm script with sbatch?
  echo "${pid_index} ${TEST_SCRIPT} -i $benchmark ${STATIC_TEST_ARGS} -m ${method} -d ${DEVICE} -n ${seq_index} -r ${RANDOM_SEQ_LEN} -l ${LUT_LIB}"
  sbatch "${slurm_script_name}.sh"
  pids[${pid_index}]=$!
}

# Launch job on LSF wiht prefix OR locally
# 
launch_lsf_job() {
  pid_index=$1
  benchmark=$2
  method=$3
  seq_index=$4
  if [ -n "${LSF_PREFIX}" ]; then
    # Add a meaningful log file to the LSF command if it's being used.
    LSF_PREFIX_LOG="-o bsub_${method}_$(basename ${BENCHMARK_DIR}).log"
  fi
  echo ${pid_index}: ${LSF_PREFIX} ${LSF_PREFIX_LOG} ${TEST_SCRIPT} -i $benchmark ${STATIC_TEST_ARGS} -m "${method}" -d ${DEVICE} -n ${seq_index} -r ${RANDOM_SEQ_LEN}
  ${LSF_PREFIX} ${LSF_PREFIX_LOG} ${TEST_SCRIPT} -i $benchmark ${STATIC_TEST_ARGS} -m "${method}" -d ${DEVICE} -n ${seq_index} -r ${RANDOM_SEQ_LEN} &
  pids[${pid_index}]=$!
}

# Turn the list of methods into an array so we have more power.
read -r -a synth_method_array <<< "${SYNTH_METHODS}"

# Dispatch ${BATCH_SIZE}-many groups of jobs in parallel and wait for them to
# complete, then continue, until all jobs are complete.
batch_controlled_launch() {
  let "i=$MIN_NUM_RUNS"
  while [ ${i} -lt ${MAX_NUM_RUNS} ]; do
    unset pids
    pids=()
    for ((j=0;j<${BATCH_SIZE} && i < ${MAX_NUM_RUNS};j++)); do
      let "k=0"
      for method in "${synth_method_array[@]}"; do
        launch_job "$(( j*${#synth_method_array[@]} + k ))" "${BENCHMARK_DIR}" "${method}" "${i}"
        let "k=k+1"
      done
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
  i=$MIN_NUM_RUNS
  tokens=0
  while [ ${i} -lt ${MAX_NUM_RUNS} ]; do
    for ((j=0;j<${BATCH_SIZE} && i < ${MAX_NUM_RUNS};j++)); do
      for method in "${synth_method_array[@]}"; do
        launch_job 0 "${BENCHMARK_DIR}" "${method}" "${i}"
        if (( tokens++ >= BATCH_SIZE )); then
          wait -n
          let "tokens=tokens-1"
        fi
      done
      let "i=i+1"
    done
  done
}

# Test is wait -n makes sense?
# Really to test if we're on bash >4.3. I mean, _really_ we want something portable.
# "All builtins return an exit status of 2 to indicate incorrect usage,
# generally invalid options or missing arguments."
# https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html
bash -c "wait -n" 2>/dev/null
return_value=$?
if (( return_value == 2 )); then
  echo "Using batch-controlled launch"
  batch_controlled_launch
else
  echo "Using token-controlled launch"
  token_controlled_launch
fi

if [ ${USE_SLURM} = true ]; then
  cat > "Makefile" <<EOT
clean:
	rm *.out *.sh
EOT
fi 
popd
