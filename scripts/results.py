import numpy as np
import pandas as pd
import glob, os.path, os
import argparse, re,csv

def lines_that_contain(string, fp):
    return [line for line in fp if string in line]

def load_data_from_dir(dirname, ip):
    data = {}
    # logs = glob.glob(os.path.normpath(dirname + "/*/test_5000.log"))
    subdirs =  glob.glob(os.path.normpath(dirname + "/tab*"))
    scripts = glob.glob(os.path.normpath(dirname + "/*/*.abc.script"))
    print("Found {} results".format(len(scripts)))
    # yosys_logs = glob.glob(os.path.normpath(dirname + "/*/yosys.log"))

    seqs=[]
    path_delay=[]; logic_delay=[]; net_delay=[]; Logic_Delay_Percentage=[]
    Slice_LUTs=[]; lut_Logic=[]; lut_mem = []; reg_ff = []; reg_latch = []
    abc_delay = [];abc_area = []

    # Populate index and sequence fields
    data["Index"] = [ os.path.basename(script).split('.')[1] for script in scripts ]
    for script in scripts:
        with open(script, "r") as fp:
             seqs.append(lines_that_contain("&scorr", fp)[0])
    data["Sequence"] = seqs
    
    # Get data from Yosys and Vivado logs
    for subdir in subdirs:
        vivado_log = glob.glob(os.path.normpath(subdir + "/test_5000.log"))
        edif_file = glob.glob(os.path.normpath(subdir + "/*.edif"))
        yosys_log = glob.glob(os.path.normpath(subdir + "/yosys.log"))
        script = glob.glob(os.path.normpath(subdir + "/*.abc.script"))
        index = os.path.basename(script[0]).split('.')[1]
        try:
            with open(vivado_log[0], "r") as fp:
                path_delay.append(re.findall(r'\d+.\d+', lines_that_contain("Path Delay", fp)[0])[0])
                fp.seek(0)
                logic_delay.append(re.findall(r'\d+.\d+', lines_that_contain("Logic Delay", fp)[0])[0])
                fp.seek(0)
                net_delay.append(re.findall(r'\d+.\d+', lines_that_contain("Net Delay", fp)[0])[0])
                fp.seek(0)
                perecentage= re.findall(r'\d+%', lines_that_contain("Logic Delay", fp)[0])[0]
                Logic_Delay_Percentage.append(perecentage[:-1])
                fp.seek(0)
                Slice_LUTs.append(re.findall(r'\d+.\d+', lines_that_contain("Slice LUTs", fp)[0])[0])
                fp.seek(0)
                lut_Logic.append(re.findall(r'\d+.\d+', lines_that_contain("LUT as Logic", fp)[0])[0])
                fp.seek(0)
                lut_mem.append(re.findall(r'\d+.\d+', lines_that_contain("LUT as Memory", fp)[0])[0])
                fp.seek(0)
                reg_ff.append(re.findall(r'\d+.\d+', lines_that_contain("Register as Flip Flop", fp)[0])[0])
                fp.seek(0)
                reg_latch.append(re.findall(r'\d+.\d+', lines_that_contain("Register as Latch", fp)[0])[0])
        except:
            path_delay.append(np.nan)
            logic_delay.append(np.nan)
            net_delay.append(np.nan)
            Logic_Delay_Percentage.append(np.nan)
            Slice_LUTs.append(np.nan)
            lut_Logic.append(np.nan)
            lut_mem.append(np.nan)
            reg_ff.append(np.nan)
            reg_latch.append(np.nan)
            
        try:
            with open(yosys_log[0], "r") as fp:
                last_if_line =  lines_that_contain("Del =", fp)[-1]
                abc_delay.append(re.findall(r'\d+.\d+',last_if_line)[0])
                abc_area.append(re.findall(r'\d+.\d+', last_if_line)[1])
        except:
            print(index)
            abc_delay.append(np.nan)
            abc_area.append(np.nan)
    data["Path_Delay"] = path_delay; data["Logic_Delay"] = logic_delay; data["Net_Delay"] = net_delay; data["Logic_Delay_Percentage"] = Logic_Delay_Percentage
    data["Slice_LUTs"] = Slice_LUTs; data["LUT_as_Logic"] = lut_Logic; data["LUT_as_Memory"] = lut_mem
    data["RegsFF"] = reg_ff; data["RegsLatch"] = reg_latch
    data["ABC_Delay"] = abc_delay; data["ABC_Area"] = abc_area
    return data


def main():
    parser = argparse.ArgumentParser(
            description='Create ABC script for each permuted sequence of synthesis transformations')
    parser.add_argument('--i', type=str, help='Results Directory')
    args = parser.parse_args()
    dir = os.path.abspath(args.i)

    bmark = os.path.basename(dir)
    ip = bmark[bmark.find('run') + 4 :]
    csv_file = ip+".out.csv"
    df_dict = load_data_from_dir(dir, ip)
    
    for key in df_dict.keys():
        print(key, len(df_dict[key]))
    
    # df["Benchmark"] = ip
    print("outputting to: " + ip+".out.csv")
    df = pd.DataFrame.from_dict(df_dict)
    df.to_csv(ip+".out.csv", sep="\t",index=False)
    # Generate scatterplots for random runs
    # dfs = load_data_from_dir("results/random*.csv")


if __name__ == "__main__":
    main()
