#!/bin/bash

SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"
RUN_DIR="${SCRIPT_DIR}/../runs"
TEST_SCRIPT="${SCRIPT_DIR}/vivado_yosys.sh"
RESULTS_DIR=  # $(readlink -f "${1:-vtr/verilog}")

# NOTE(aryap): 'realpath' is a nice tool to do 'readlink -f' which is itself a
# nice too to recursively expand symlinks, but it isn't available on BWRC
# servers, and we have a more portable solution so I'm not installing it.

while [ "$1" != "" ]; do
  case $1 in
    -o | --output )         shift
                            RUN_DIR="$(readlink -f "$1")"
                            ;;
    -i | --input )          shift
                            RESULTS_DIR="$(readlink -f "$1")"
                            ;;
    * )                     echo "computer says no: ${1}"
                            exit 1
  esac
  shift
done


ip=$( echo $(basename -- ${RESULTS_DIR}) | sed 's/run\_//' )
# FIXME(aryap): also in vivado_yosys.sh: .gz inputs must be expanded to
# .v/.vhdl and merged with the other inputs, and then sources de-duplicated.
# Could use sort/uniq? Or write the algorithm in bash (worse). Expanding .gz
# inputs must be removed from the vivado_yosys.sh script so it doesn't have to
# deal with with multiple runs clobbering the same test scripts.

# TODO(aryap): It'd be nice to be able to handle a list of sources, or any
# expansion.
if [ -d "${RESULTS_DIR}" ]; then
  # TODO(aryap): This is a dangerously-bash bashism
  shopt -s nullglob
  #benchmarks=( ${BENCHMARK_DIR}/*.{v,vhdl,gz} )
  logs=( ${RESULTS_DIR}/*/test_5000.log )
  scripts=( ${RESULTS_DIR}/*/*.abc.script )
  num_results=${#logs[@]}
  echo "Found ${num_results} results:"
#   for file in "${logs[@]}"; do
#     echo "  ${file}"
#   done
  shopt -u nullglob
elif [ -f "${RESULTS_DIR}" ]; then
  # Input is just one file
  logs="${RESULTS_DIR}"
  num_results=1
else
  echo "Unsuitable input source: ${RESULTS_DIR}"
  exit 3
fi
echo "Input is ${RESULTS_DIR}: ${#logs[@]} files"

rm $ip.out.csv
printf "Sequence\tPathDelay\tLogicDelay\tNetDelay\tLUTsLogic\tRegsFF\tRegsLatch\n" >> $ip.out.csv

let "i=0"
while [ ${i} -lt ${num_results} ]; do
    SEQ=$( cat ${scripts[i]})
    DELAY_NS=$(grep "Path Delay"  ${logs[i]} | sed 's/[^0-9.]*//g')
    LOGIC_DELAY_NS=$( grep "Logic Delay"  ${logs[i]} |  sed -e 's/[^0-9.(%)]*//g; s/%/%%/g' )
    NET_DELAY_NS=$( grep "Net Delay"  ${logs[i]} |  sed -e 's/[^0-9.(%)]*//g; s/%/%%/g' )
    LUT_LOGIC=$( grep "LUT as Logic" ${logs[i]} |  sed 's/[^0-9]*|//g; s/[ \t]*\([0-9]\{1,\}\).*/\1/' )
    REG_FF=$( grep "Register as Flip Flop" ${logs[i]} |  sed 's/[^0-9]*|//g; s/[ \t]*\([0-9]\{1,\}\).*/\1/' )
    REG_LATCH=$( grep "Register as Latch" ${logs[i]} |  sed 's/[^0-9]*|//g; s/[ \t]*\([0-9]\{1,\}\).*/\1/' )
    printf "$SEQ\t$DELAY_NS\t$LOGIC_DELAY_NS\t$NET_DELAY_NS\t$LUT_LOGIC\t$REG_FF\t$REG_LATCH\n" >> $ip.out.csv

    let "i=i+1"
done