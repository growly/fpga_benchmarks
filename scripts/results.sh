#!/bin/bash

SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"
RUN_DIR="${SCRIPT_DIR}/../runs"
TEST_SCRIPT="${SCRIPT_DIR}/vivado_yosys.sh"
RESULTS_DIR=  # $(readlink -f "${1:-vtr/verilog}")
USE_SLURM=false

while [ "$1" != "" ]; do
  case $1 in
    -o | --output )         shift
                            RUN_DIR="$(readlink -f "$1")"
                            ;;
    -i | --input )          shift
                            RESULTS_DIR="$(readlink -f "$1")"
                            ;;
    -s | --slurm)           USE_SLURM=true
                            ;;

    * )                     echo "computer says no: ${1}"
                            exit 1
  esac
  shift
done

ip=$( echo $(basename -- ${RESULTS_DIR}) | sed 's/run\_//' )

get_results() {
    echo 'local'
    if [ -d "${RESULTS_DIR}" ]; then
    shopt -s nullglob
    logs=( ${RESULTS_DIR}/*/test_5000.log )
    scripts=( ${RESULTS_DIR}/*/*.abc.script )
    yosys_logs=( ${RESULTS_DIR}/*/yosys.log )
    num_results=${#logs[@]}
    echo "Found ${num_results} results:"
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
    printf "Index\tSequence\tPath_Delay\tLogic_Delay\tNet_Delay\tLogic_to_Net_Ratio\tSlice_LUTs\tLUTs_as_Memory\tLUTs_as_Logic\tRegsFF\tRegsLatch\tABC_Delay\tABC_Area\n" >> $ip.out.csv

    let "i=0"
    while [ ${i} -lt ${num_results} ]; do
	SEQ=$( grep "&scorr" ${scripts[i]})
	DELAY_NS=$(grep "Path Delay"  ${logs[i]} | sed 's/[^0-9.]*//g')
	LOGIC_DELAY_NS=$( grep "Logic Delay"  ${logs[i]} |  sed -e 's/[^0-9.(%)]*//g; s/%/%%/g' )
	NET_DELAY_NS=$( grep "Net Delay"  ${logs[i]} |  sed -e 's/[^0-9.(%)]*//g; s/%/%%/g' )
	LOGIC_NET_RATIO=$( grep "Logic Delay"  ${logs[i]} |  sed -e 's/^.*(//g; s/[^0-9]*//g')
	SLICE_LUTS=$( grep "Slice LUTs" ${logs[i]} |  sed 's/[^0-9]*|//g; s/[ \t]*\([0-9]\{1,\}\).*/\1/' )
	LUT_LOGIC=$( grep "LUT as Logic" ${logs[i]} |  sed 's/[^0-9]*|//g; s/[ \t]*\([0-9]\{1,\}\).*/\1/' )
	LUT_MEM=$( grep "LUT as Memory" ${logs[i]} |  sed 's/[^0-9]*|//g; s/[ \t]*\([0-9]\{1,\}\).*/\1/' )
	REG_FF=$( grep "Register as Flip Flop" ${logs[i]} |  sed 's/[^0-9]*|//g; s/[ \t]*\([0-9]\{1,\}\).*/\1/' )
	REG_LATCH=$( grep "Register as Latch" ${logs[i]} |  sed 's/[^0-9]*|//g; s/[ \t]*\([0-9]\{1,\}\).*/\1/' )
   
	ABC_DELAY=$( grep "Del = " ${yosys_logs[i]} | tail -n 1 | sed -e 's/.*Del = \([^\.]*\).*/\1/g')
	ABC_AREA=$( grep "Ar = " ${yosys_logs[i]} | tail -n 1 | sed -e 's/.*Ar = \([^\.]*\).*/\1/g')
   
	printf "$i\t$SEQ\t$DELAY_NS\t$LOGIC_DELAY_NS\t$NET_DELAY_NS\t$LOGIC_NET_RATIO\t$SLICE_LUTS\t$LUT_MEM\t$LUT_LOGIC\t$REG_FF\t$REG_LATCH\t$ABC_DELAY\t$ABC_AREA\n" >> ${ip}.out.csv
	let "i=i+1"
    done
}

get_results_slurm() {
    echo "entering!"
    cat > "result_gen_${ip}.sh" <<EOT
#!/bin/bash
# generated at $(date) by results.sh
# Job name:
#SBATCH --job-name=results_${ip}
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
if [ -d "${RESULTS_DIR}" ]; then
    shopt -s nullglob
    logs=( ${RESULTS_DIR}/*/test_5000.log )
    scripts=( ${RESULTS_DIR}/*/*.abc.script )
    num_results=${#logs[@]}
    echo "Found ${num_results} results:"
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
   printf "$SEQ\t$DELAY_NS\t$LOGIC_DELAY_NS\t$NET_DELAY_NS\t$LUT_LOGIC\t$REG_FF\t$REG_LATCH\n" >> ${ip}.out.csv
   let "i=i+1"
 done
EOT
}

main() {
    get_results

}

main
