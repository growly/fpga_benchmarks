#!/bin/bash

# Adapted from https://github.com/YosysHQ/yosys-bench/blob/cmp/scripts/vivado_min_period.sh
# Adapted from https://github.com/cliffordwolf/picorv32/blob/d046cbfa4986acb50ef6b6e5ff58e9cab543980b/scripts/vivado/tabtest.sh

# "exit immediately if a command exits with a non-zero status"
#set -e

input=
dev="xc7a200"
grade=1
speed=5000  # picoseconds
synth="yosys-abc9" # yosys | yosys-abc9 | vivado
clean=false
idx=0
RANDOM_SEQ_LEN=0
LUT_LIBRARY=0
SCRIPT_DIR="$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"


while [ "$1" != "" ]; do
  case $1 in
    -i | --input )          shift
                            input="$1"
                            ;;
    -n | --index )          shift
                            idx="$1"
                            ;;
    -r | --random )         shift
                            RANDOM_SEQ_LEN="$1"
                            ;;
    -l | --lut_library )    shift
                            LUT_LIBRARY="$1"
                            ;;
    -d | --device )         shift
                            dev="$1"
                            ;;
    -g | --grade )          shift
                            grade="$1"
                            ;;
    -s | --speed )          shift
                            speed="$1"
                            ;;
    -m | --synth_method )   shift
                            synth="$1"
                            ;;
    -c | --clean )          shift
                            clean=true
                            ;;
    * )                     echo "computer says no: ${1}"
                            exit 1
  esac
  shift
done

if ! [ -f "${input}" ]; then
  echo "Input file not found: ${input}"
  exit 1
fi
path=$(readlink -f "${input}")
echo "Starting '${synth}' on '${path}'"
ip="$(basename -- ${path})"
ip=${ip%.gz}
ip=${ip%.*}

# NOTE: You can export a spreadsheet of supported devices from Vivado's Project
# Settings dialog.
case "${dev}" in
  xc7a) xl_device="xc7a100tcsg324-${grade}" ;;
  xc7a200) xl_device="xc7a200tffv1156-${grade}" ;;
  xc7k) xl_device="" ;;
  xc7v) xl_device="" ;;
  xcku) xl_device="xcku035-ffva1156-${grade}-e" ;;
  xcvu2104) xl_device="xcvu35p-fsvh2104-${grade}-e" ;; # needs license
  xckup) xl_device="" ;;
  xcvu2892) xl_device="xcvu35p-fsvh2892-${grade}-e" ;; # needs license
  xcvu440) xl_device="xcvu440-flga2892-${grade}-i" ;; # needs license
esac

YOSYS=$(command -v yosys)
#YOSYS=${YOSYS:-/home/arya/src/yosys/yosys}
if [[ "${synth}" == *"yosys"* ]] && [ ! -x "${YOSYS}" ]; then
  echo "yosys required for synth but executable not usable: ${YOSYS}"
  exit 10
fi

# VIVADO=${VIVADO:-/opt/Xilinx/Vivado/2020.1/bin/vivado}
VIVADO=$(command -v vivado)
if [[ "${synth}" == *"vivado"* ]] && [ ! -x "${VIVADO}" ]; then
  echo "vivado required for synth but executable not usable: ${VIVADO}"
  exit 11
fi

# echo "speed=${speed}"
# echo "dev=${dev}"
# echo "grade=${grade}"
# echo "ip=${ip}"
# echo "path=${path}"
# echo "clean=${clean}"
# echo "xl_device=${xl_device}"
# echo "YOSYS=${YOSYS}"
# echo "VIVADO=${VIVADO}"

test_name="tab_${synth}_${ip}_${dev}_${idx}"
if [ ${RANDOM_SEQ_LEN} -gt 0  ]; then
  test_name="tab_${synth}_${ip}_${dev}_random_${idx}"
fi 

if ${clean}; then
  rm -rf "${test_name}"
fi
mkdir -p ${test_name}
cd ${test_name}
# rm -f ${ip}.edif

# parameter : index start_idx ~ last_idx
synth_case() {
  run_name="test_${1}"
  xdc_file="test_${1}.xdc"

  if [ -f test_${1}.txt ]; then
    echo "${test_name} reusing cached test_${1}."
    return
  fi

  cat > test_${1}.tcl <<EOT
# generated at $(date)
set_param general.maxThreads 1
set_property IS_ENABLED 0 [get_drc_checks {PDRC-43}]
EOT

  pwd=${PWD}
  if [ "${synth}" = "vivado" ]; then
    cat >> test_${1}.tcl <<EOT
cd $(dirname ${path})
EOT
    # FIXME(aryap): When spawning these jobs in parallel. If one jobs reads the
    # .gz and another reads a .v (created on a previous run and included as an
    # input to this run), they might both write to the same .tcl file here.
    #if [ "${path##*.}" == "gz" ]; then
    #  # This is portable to BWRC machines:
    #  gunzip -c ${path} > ${path%.gz}
    #  # This is too modern:
    #  # gunzip -f -k ${path}
    #fi
    cat >> test_${1}.tcl <<EOT
if {[file exists "$(dirname ${path})/${ip}_vivado.tcl"] == 1} {
  source ${ip}_vivado.tcl
} else {
  read_verilog $(basename ${path%.gz})
  #read_verilog ${path}
}
if {[file exists "$(dirname ${path})/${ip}.top"] == 1} {
  set fp [open $(dirname ${path})/${ip}.top]
  set_property TOP [string trim [read \$fp]] [current_fileset]
} else {
  set_property TOP [lindex [find_top] 0] [current_fileset]
}
cd ${pwd}
read_xdc -unmanaged ${xdc_file}
synth_design -part ${xl_device} -mode out_of_context ${SYNTH_DESIGN_OPTS}
opt_design -directive Explore
EOT

  else
    edif="${ip}.edif"
    synth_with_abc9=
    synth_abc9=0
    mem_file="$SCRIPT_DIR/include/dual_port_ram.v"
    if [ "${synth}" = "yosys-abc9" ]; then
      synth_with_abc9="-abc9"
      synth_abc9=1
    fi
    if [ -f "${edif}" ]; then
      echo "${test_name} reusing cached ${edif}"
    else
      if [ -f "$(dirname ${path})/${ip}.ys" ]; then
        echo "script ${ip}.ys" > ${ip}.ys
      elif [ ${path:-5} == ".vhdl" ]; then
          echo "read -vhdl $(basename ${path})" > ${ip}.ys
      else
          #echo "read_verilog $(basename ${path})" > ${ip}.ys
          echo "read_verilog ${path}" > ${ip}.ys
      fi

      # If the top is specified in a .top file, specify that to Yosys so that
      # the hierarchy can be trimmed of other garbage (I mean, unnecessary
      # artifacts).
      top_file="$(dirname ${path})/${ip}.top"
      if [ -f "${top_file}" ]; then
        echo "hierarchy -check -top $(<${top_file})" >> ${ip}.ys
      fi
      python3 $SCRIPT_DIR/gen_synthesis_script.py --in_idx=${2} --random_seq_len=${3} --abc9=$synth_abc9 --lut_library $4 > ${ip}.${2}.abc.script
      cat >> ${ip}.ys <<EOT
read_verilog ${mem_file}
synth_xilinx -dff -flatten -noiopad ${synth_with_abc9} -edif ${edif} -script  ${ip}.${2}.abc.script
#synth_xilinx -dff -flatten -noiopad ${synth_with_abc9} -edif ${edif} 
write_verilog -noexpr -norename ${pwd}/${ip}_syn.v
EOT
# synth_xilinx -flatten ${synth_with_abc9} -edif ${edif}

      echo "${test_name} running ${ip}.ys..."
      #pushd $(dirname ${path}) > /dev/null
    #   if ! ${YOSYS} -l ${pwd}/yosys.log ${pwd}/${ip}.ys > /dev/null 2>&1; then
    #     cat ${pwd}/yosys.log
    #     exit 1
    #   fi
    #   #popd > /dev/null
    #   mv yosys.log yosys.txt
      ${YOSYS} ${pwd}/${ip}.ys -l ${pwd}/yosys.log > /dev/null 2>&1
#      ${YOSYS} ${pwd}/${ip}.ys > /dev/null 2>&1
    fi

    cat >> test_${1}.tcl <<EOT
read_edif ${edif}
read_xdc -unmanaged ${xdc_file}
link_design -part ${xl_device} -mode out_of_context -top ${ip}
EOT
  fi

  cat > "${xdc_file}" <<EOT
# Auto-generated XDC file; read with read_xdc -unmanaged
EOT
  speed_ns=$(printf %.2f "$((speed))e-3")
  clock_file="$(dirname ${path})/${ip}.clock"
  clock_expr=
  if [ -f "${clock_file}" ]; then
    clock_expr=$(<${clock_file})
    cat >> "${xdc_file}" <<EOT
if {[llength [get_ports -quiet -nocase ${clock_expr}]] == 0} {
  puts "ERROR: Explicit clock ${clock_expr} from ${clock_file} not found"
}
create_clock -period ${speed_ns} ${clock_expr}
EOT
  else
    clock_expr="[get_ports -quiet -nocase -regexp .*cl(oc)?k.*]"
    cat >> "${xdc_file}" <<EOT
if {[llength ${clock_expr}] != 0} {
  create_clock -period ${speed_ns} ${clock_expr}
} else {
  puts "WARNING: Clock constraint omitted because expr \"${clock_expr}\" matched nothing."
}
EOT
  fi
  cat >> test_${1}.tcl <<EOT
#report_timing_summary
report_design_analysis
report_utilization
# For now, don't do place and route
# place_design -directive Explore
# route_design -directive Explore
# report_utilization
# report_timing -no_report_unconstrained
# report_clocks
# report_design_analysis
# report_power
# report_io
EOT

  echo "${test_name} running test_${1}..."
  if ! $VIVADO -nojournal -log test_${1}.log -mode batch -source test_${1}.tcl > /dev/null 2>&1; then
    cat test_${1}.log
    exit 1
  fi
#   mv test_${1}.log test_${1}.txt
}


report_timing() {
  timing_results_file="test_${1}.log"
  if [ ! -f "${timing_results_file}" ]; then
    echo "${test_name} broken run; could not find timing results: ${timing_results_file}"
    exit 3
  fi

  if grep 'Delay' "${timing_results_file}"; then
    grep 'Delay' "${timing_results_file}" > timing_${2}.txt
  else
    echo "${test_name} broken run, could not find 'Path Delay' in results file: ${timing_results_file}"
    exit 4
  fi
}

# for idx in $(seq $start_idx $end_idx)
# do 
#     synth_case  "${speed}"  "${idx}"
#     report_timing   "${speed}"    "${idx}"
# done
echo "Running for Sequence # ${idx}"
synth_case  ${speed}  ${idx}  ${RANDOM_SEQ_LEN} ${LUT_LIBRARY}
# report_timing   "${speed}"    "${idx}"

remaining_iterations=0
speed_upper_bound=${speed}
speed_lower_bound=0
met_timing=false

# TODO(aryap): Might not want this to exit the script if a run is broken, since
# previous runs might have had results we want to keep (i.e. dump to
# 'best_speed.txt').
check_timing() {
  timing_results_file="test_${1}.txt"
  if [ ! -f "${timing_results_file}" ]; then
    echo "${test_name} broken run; could not find timing results: ${timing_results_file}"
    exit 3
  fi

  if grep -qE '^Slack \(MET\)' "${timing_results_file}"; then
    met_timing=true
  elif grep -qE '^Slack \(VIOLATED\)' "${timing_results_file}"; then
    met_timing=false
  else
    echo "${test_name} broken run, could not find 'Slack: (VIOLATED|MET)' in results file: ${timing_results_file}"
    exit 4
  fi
}

last_speed=
while [ ${remaining_iterations} -gt 0 ]; do
  echo "${test_name} Commencing iteration @ speed: ${speed}"

  synth_case "${speed}"

  check_timing "${speed}"

  if [ "${met_timing}" = true ]; then
    speed_upper_bound=${speed}
    best_speed=${speed}
    echo "${test_name} MET      timing @ speed: ${speed}"
  elif [ "${met_timing}" = false ]; then
    speed_lower_bound=${speed}
    echo "${test_name} VIOLATED timing @ speed: ${speed}"
  fi
  last_speed=${speed}
  speed=$(((speed_upper_bound + speed_lower_bound) / 2))
  remaining_iterations=$((remaining_iterations - 1))

  # If we're trying to run the same speed twice in a row, we should stop.
  if [ -n "${last_speed}" -a "${last_speed}" = "${speed}" ]; then
    echo "${test_name} search not making progress since last speed: ${speed}"
    break
  fi
done

if [ -n "${best_speed}" ]; then
  echo "${best_speed}" > best_speed.txt
fi
