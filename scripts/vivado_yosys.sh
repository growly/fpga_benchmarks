#!/bin/bash

# Adapted from https://github.com/YosysHQ/yosys-bench/blob/cmp/scripts/vivado_min_period.sh
# Adapted from https://github.com/cliffordwolf/picorv32/blob/d046cbfa4986acb50ef6b6e5ff58e9cab543980b/scripts/vivado/tabtest.sh

# "exit immediately if a command exits with a non-zero status"
#set -e

input=
dev="xc7a200"
grade=1
speed=50
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
echo "Running '${synth}' on '${path}'"
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
esac

YOSYS=${YOSYS:-/home/arya/src/yosys/yosys}
VIVADO=${VIVADO:-/opt/Xilinx/Vivado/2020.1/bin/vivado}

# echo "speed=${speed}"
# echo "dev=${dev}"
# echo "grade=${grade}"
# echo "ip=${ip}"
# echo "path=${path}"
# echo "clean=${clean}"
# echo "xl_device=${xl_device}"
# echo "YOSYS=${YOSYS}"
# echo "VIVADO=${VIVADO}"

if ${clean}; then
  rm -rf tab_${synth}_${ip}_${dev}_${grade}
fi
mkdir -p tab_${synth}_${ip}_${dev}_${grade}
cd tab_${synth}_${ip}_${dev}_${grade}
#rm -f ${ip}.edif

synth_case() {
  if [ -f test_${1}.txt ]; then
    echo "Reusing cached tab_${synth}_${ip}_${dev}_${grade}/test_${1}."
    return
  fi

  cat > test_${1}.tcl <<EOT
set_param general.maxThreads 1
set_property IS_ENABLED 0 [get_drc_checks {PDRC-43}]
EOT

  pwd=${PWD}
  if [ "${synth}" = "vivado" ]; then
    cat >> test_${1}.tcl <<EOT
cd $(dirname ${path})
EOT
    if [ "${path##*.}" == "gz" ]; then
      gunzip -f -k ${path}
    fi
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
read_xdc test_${1}.xdc
synth_design -part ${xl_device} -mode out_of_context ${SYNTH_DESIGN_OPTS}
opt_design -directive Explore
EOT

  else
    edif="${ip}.edif"
    synth_with_abc9=
    if [ "${synth}" = "yosys-abc9" ]; then
      synth_with_abc9="-abc9"
    fi
    if [ -f "${edif}" ]; then
      echo "Reusing cached tab_${synth}_${ip}_${dev}_${grade}/${edif}"
    else
      if [ -f "$(dirname ${path})/${ip}.ys" ]; then
        echo "script ${ip}.ys" > ${ip}.ys
      elif [ ${path:-5} == ".vhdl" ]; then
          echo "read -vhdl $(basename ${path})" > ${ip}.ys
      else
          #echo "read_verilog $(basename ${path})" > ${ip}.ys
          echo "read_verilog ${path}" > ${ip}.ys
      fi

      cat >> ${ip}.ys <<EOT
synth_xilinx -dff -flatten ${synth_with_abc9} -edif ${edif}
write_verilog -noexpr -norename ${pwd}/${ip}_syn.v
EOT

      echo "Running tab_${synth}_${ip}_${dev}_${grade}/${ip}.ys.."
      #pushd $(dirname ${path}) > /dev/null
      if ! ${YOSYS} -l ${pwd}/yosys.log ${pwd}/${ip}.ys > /dev/null 2>&1; then
        cat ${pwd}/yosys.log
        exit 1
      fi
      #popd > /dev/null
      mv yosys.log yosys.txt
    fi

    cat >> test_${1}.tcl <<EOT
read_edif ${edif}
read_xdc test_${1}.xdc
link_design -part ${xl_device} -mode out_of_context -top ${ip}
EOT
  fi

  cat > test_${1}.xdc <<EOT
create_clock -period ${speed:0: -1}.${speed: -1} [get_ports -nocase -regexp .*cl(oc)?k.*]
EOT
  cat >> test_${1}.tcl <<EOT
report_design_analysis
place_design -directive Explore
route_design -directive Explore
report_utilization
report_timing -no_report_unconstrained
report_design_analysis
EOT

  echo "Running tab_${synth}_${ip}_${dev}_${grade}/test_${1}..."
  if ! $VIVADO -nojournal -log test_${1}.log -mode batch -source test_${1}.tcl > /dev/null 2>&1; then
    cat test_${1}.log
    exit 1
  fi
  mv test_${1}.log test_${1}.txt
}

synth_case "${speed}"
