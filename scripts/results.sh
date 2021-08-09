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
    if [ -d "${RESULTS_DIR}" ]; then
	shopt -s nullglob
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
    if [ ${USE_SLRUM}=true ]; then
	get_results_slurm
    else
	get_results
    fi
}

main
