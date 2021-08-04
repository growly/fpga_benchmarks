#!/bin/bash

# Adapted from https://github.com/YosysHQ/yosys-bench/blob/cmp/scripts/vivado_min_period.sh
# Adapted from https://github.com/cliffordwolf/picorv32/blob/d046cbfa4986acb50ef6b6e5ff58e9cab543980b/scripts/vivado/tabtest.sh

# "exit immediately if a command exits with a non-zero status"
#set -e

input=
dev="xc7a200"
grade=1
speed=5000  # picoseconds
synth="yosys" # yosys | yosys-abc9 | vivado
clean=false

while [ "$1" != "" ]; do
  case $1 in
    -i | --input )          shift
                            input="$1"
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

echo "speed=${speed}"
echo "dev=${dev}"
echo "grade=${grade}"
echo "ip=${ip}"
echo "path=${path}"
echo "clean=${clean}"
echo "xl_device=${xl_device}"
echo "YOSYS=${YOSYS}"
echo "VIVADO=${VIVADO}"

test_name="tab_${synth}_${ip}_${dev}_${grade}"

if ${clean}; then
  rm -rf "${test_name}"
fi
mkdir -p ${test_name}
cd ${test_name}
#rm -f ${ip}.edif

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
  edif="${ip}.edif"
  synth_with_abc9=
  if [ "${synth}" = "yosys-abc9" ]; then
    synth_with_abc9="-abc9"
  fi
  if [ -f "${edif}" ]; then
    echo "${test_name} reusing cached ${edif}"
  else
    # if [ -f "$(dirname ${path})/${ip}.ys" ]; then
    #   echo "script ${ip}.ys" > ${ip}.ys
    # elif [ ${path:-5} == ".vhdl" ]; then
    #     echo "read -vhdl $(basename ${path})" > ${ip}.ys
    # else
    #     #echo "read_verilog $(basename ${path})" > ${ip}.ys
    #     echo "read_verilog ${path}" > ${ip}.ys
    # fi

    # # If the top is specified in a .top file, specify that to Yosys so that
    # # the hierarchy can be trimmed of other garbage (I mean, unnecessary
    # # artifacts).
    # top_file="$(dirname ${path})/${ip}.top"
    # if [ -f "${top_file}" ]; then
    #   echo "hierarchy -check -top $(<${top_file})" >> ${ip}.ys
    # fi
# Part running YOSYS
      # echo -e "read_verilog $path; write_blif $ip.blif " | $YOSYS %TODO: read verilog and output BLIF
      ln -s ../scripts/abc .
      design=$ip
      ftune_input=$path #TODO: use generated BLIF files $ip.blif in tab_.. dir
      repeat=1
      iteration=6
      target=4
      sample=5
      stage=1
      echo "ftune is working on file: " ${path}
      echo "*************  level-0 tuning starts *********** "
      # level-1 tuning
      echo -e "ftune -d $ftune_input -r $repeat -t $target -p 1 -i $iteration -s $sample" | ./abc
      
      ## randomly pick one of the ftune script
      shuf -n 1 $ftune_input.script > $design.script
      echo -e "read $ftune_input; source $design.script;strash;write internal.blif;ps" | ./abc
      
      for (( c=1; c<=$stage; c++ ))
      do
        # level-2 tuning
        echo "*************  level[$c] tuning starts *********** "
        echo -e "ftune -d internal.blif -r $repeat -t $target -p 1 -i $iteration -s $sample" | ./abc
        ## randomly pick one of the ftune script
        shuf -n 1 internal.blif.script > $design.script
        echo -e "read internal.blif; source $design.script;write internal.blif" | ./abc
      done

      cp internal.blif $design.ftune.blif
      cat >> ${ip}.ys <<EOT
read_blif ${design}.ftune.blif 
write_edif ${edif}
EOT
      # echo "${test_name} running ${ip}.ys..."
      # #pushd $(dirname ${path}) > /dev/null
      # if ! ${YOSYS} -l ${pwd}/yosys.log ${pwd}/${ip}.ys > /dev/null 2>&1; then
      #   cat ${pwd}/yosys.log
      #   exit 1
      # fi
      # #popd > /dev/null
      # mv yosys.log yosys.txt
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
report_design_analysis
report_utilization
report_timing -no_report_unconstrained
report_clocks
report_design_analysis
report_power
report_io
EOT

  echo "${test_name} running test_${1}..."
  if ! $VIVADO -nojournal -log test_${1}.log -mode batch -source test_${1}.tcl > /dev/null 2>&1; then
    cat test_${1}.log
    exit 1
  fi
  mv test_${1}.log test_${1}.txt
}


# ONLY ONE RUN FOR NOW

remaining_iterations=1
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

# if [ -n "${best_speed}" ]; then
#   echo "${best_speed}" > best_speed.txt
# fi