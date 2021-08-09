#!/bin/bash
# generated at $(date) by results.sh
# Job name:
#SBATCH --job-name=results_run_abc9_or1200
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
ip="lib1_or1200"
RESULTS_DIR="/global/home/users/minwoo_kang/fpga_benchmarks/run_$ip"

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
