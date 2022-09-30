#!/usr/bin/python3

import argparse
import collections
import csv
import os 
from os.path import isfile, join
import time
import re
from collections import defaultdict
import sys

import functools
import operator


PATH_TO_YOSYS = "/users/bbarzen/workspace/yosys/yosys-nodc2"
PATH_TO_VIVADO = "/tools/xilinx/Vivado/2022.1/bin/vivado"

TARGET_XL_DEVICE_ID = "xc7a200tffv1156-1"

def write_csv(results_dict, num_runs, csvpath):
	with open(csvpath, 'w', newline='') as csvfile:
		csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		print(results_dict)
		for method, designs in results_dict.items():
			csvwriter.writerow([method])
			csvwriter.writerow(['design'] + [i for i in range(num_runs)])
			for design, run_ids in designs.items():
				csvwriter.writerow([design] + [t for i,t in run_ids.items()])

def write_xdc():
	xdc_file = open("/tmp/vivado.xdc",'w')
	xdc_file.write(
"# Auto-generated XDC file; read with read_xdc -unmanaged\n"+
"if {[llength [get_ports -quiet -nocase -regexp .*cl(oc)?k.*]] != 0} {\n"+
"\tcreate_clock -period 30.00 [get_ports -quiet -nocase -regexp .*cl(oc)?k.*]\n"+
"} else {\n"+
"\tputs \"WARNING: Clock constraint omitted.\"\n"+
"}\n"
)
	xdc_file.close()


def run_yosys(design_files, results_dict, source_dir, run_id, use_abc9):
	for design in design_files:
		yosys_script_path = "/tmp/"+design+".ys"
		yosys_script = open(yosys_script_path, 'w')
		yosys_script.write(
"read_verilog -nomem2reg -yydebug {}/{}\n".format(source_dir, design)+
"synth_xilinx -dff -flatten -noiopad {} -edif {}.edif".format("-abc9" if use_abc9 else "", design[:-2])
)
		yosys_script.close()
		print("Run yosys{}-{}-{}".format("-abc9" if use_abc9 else "", design, run_id))
		start_time = time.time()
		os.system("{} -l /tmp/yosys{}-{}-{}.log {} > /dev/null 2>&1".format(PATH_TO_YOSYS, "-abc9" if use_abc9 else "", design, run_id, yosys_script_path))
		end_time = time.time()
		results_dict["yosys-abc9" if use_abc9 else "yosys"][design][run_id] = end_time - start_time
	    

def run_vivado(design_files, results_dict, source_dir, run_id):
	for design in design_files:
		vivado_script_path = "/tmp/"+design+".tcl"
		vivado_script = open(vivado_script_path, 'w')
		vivado_script.write(
"set_param general.maxThreads 1\n" +
"set_property IS_ENABLED 0 [get_drc_checks {PDRC-43}]\n" + 
"cd {}\n".format(source_dir) + 
"read_verilog {}\n".format(design) + 
"set_property TOP [lindex [find_top] 0] [current_fileset]\n" + 
"cd /tmp/\n" + 
"read_xdc -unmanaged vivado.xdc\n" + 
"synth_design -part {} -mode out_of_context \n".format(TARGET_XL_DEVICE_ID) + 
"opt_design -directive Explore\n"
)
		vivado_script.close()
		print("Run vivado-{}-{}".format(design, run_id))
		start_time = time.time()
		os.system("{} -nojournal -log /tmp/vivado-{}-{}.log -mode batch -source {} > /dev/null 2>&1".format(PATH_TO_VIVADO, design, run_id, vivado_script_path))
		end_time = time.time()
		results_dict["vivado"][design][run_id] = end_time - start_time

		
	

def main():

	parser = argparse.ArgumentParser(
	description='Run Vivado, Yosys and Yosys-ABC9 flow and measure runtime.')
	parser.add_argument('--design_dir', type=str, help='Directory which contains Designs')
	parser.add_argument('--result_csv', type=str, help='Output File Path')
	parser.add_argument('--num_rounds', type=int, help='Number of Runs per Software')

	args = parser.parse_args()
	
	if len(sys.argv) < 4:
		parser.print_help()
		parser.exit()
	
	source_dir = None
	try:
		source_dir = os.path.realpath(args.design_dir)
	except:
		print('Could not find results in {}'.format(source_dir), file=sys.stderr)
		sys.exit(1)		
	
	# Create list of designs, prepare result dict, write clock file
	design_files = [f for f in os.listdir(source_dir) if isfile(join(source_dir, f)) and f.endswith(".v")]	
	results_dict = defaultdict(lambda: defaultdict(dict))
	write_xdc()

	for i in range(args.num_rounds):	
		run_vivado(design_files, results_dict, source_dir, i)	
		run_yosys(design_files, results_dict, source_dir, i, False)
		#run_yosys(design_files, results_dict, source_dir, i, True)

	write_csv(results_dict, args.num_rounds, args.result_csv)
	

if __name__ == '__main__':
	main()
