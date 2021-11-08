import numpy as np
import matplotlib as mpl
mpl.use('Agg')

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import glob, os.path, os

#global params
fig_dims = (12,8)
axis_label = 12
legend_label = 12
axis_scale = 2.0
default_abc9_script="&scorr;&sweep;&dc2;&dch -f;&if -W 300 -K 6 -v;&mfs;"

# Load the data as Pandas DataFrame
def load_data(pathname):
    filename=os.path.basename(pathname)
    tag=filename[filename.find('_') + 1 :filename.find('.out.csv')]
    data = pd.read_csv(pathname, delimiter="\t")
    data["Benchmark"] = tag
    return data, tag

def load_data_from_dir(search):
    dfs = []
    search_path = os.path.normpath(os.path.join(os.getcwd(), search))
    csvs = glob.glob(search_path)
    for f in csvs:
        filename=os.path.basename(f)
        tag=filename[filename.find('_') + 1:filename.find('.out.csv')]
        data = pd.read_csv(f, delimiter="\t")
        data["Benchmark"] = tag
        
        # parse into percentage
        # col = data["LogicDelay"].astype(str).transform(lambda x: x[x.find('(')+1, x.find('%')])
#        data["Logic Delay Ratio"] =  [s if isinstance(s, float) else int(s[s.find('(')+1: s.find('%')]) / 100  for  s in data["LogicDelay"].to_numpy()]
        dfs.append(data)
    return dfs

"""
    Plot a single (scatter/line/etc) plot for a benchmark
    @params: 
    
"""
def plot_single (df, title, y_vars, plot_type="scatter-ratios"):
    sns.set_style("darkgrid")
    fig = plt.gcf()
    fig.set_size_inches(fig_dims)
    
    yosys_baseline = df.loc[df['Sequence'] == default_abc9_script]
    with sns.plotting_context(font_scale=axis_scale):
        plt.axvline(yosys_baseline.iloc[0][y_vars[0]], ls='--', color='black', lw=0.7)
        plt.axhline(yosys_baseline.iloc[0][y_vars[1]], ls='--', color='black', lw=0.7)

        if (plot_type == "scatter-ratios"):
            df["Logic to Net Delay Ratio (%)"] = df["Logic_to_Net_Ratio"]
            ax = sns.scatterplot(x=y_vars[0], y = y_vars[1],  data=df, hue="Logic to Net Delay Ratio (%)", palette="coolwarm");
        elif (plot_type == "scatter"):
            ax = sns.scatterplot(x=y_vars[0], y = y_vars[1],  data=df);
        else :
            ax = sns.lineplot(x=y_vars[0], y = y_vars[1],  data=df);
        ax.set_xlabel(y_vars[0], fontsize=axis_label, weight='bold')
        ax.set_ylabel(y_vars[1], fontsize=axis_label, weight='bold')
        #plt.legend(fontsize=legend_label,loc=1, prop={'weight': 'bold'})
        plt.title(title+" (N={})".format(df[y_vars[1]].count()), fontsize=axis_label, weight='bold')
    plt.savefig(title+'_'+y_vars[0]+'_'+y_vars[1]+'.png',  format='png', dpi=300)
    plt.close() 

"""
    From a list of DataFrames, plot inidividual plots for each DF
"""
def plot_singles(dfs, title, y_vars, plot_type):
    for df in dfs:
        bmark = df["Benchmark"][0]
        plot_single(df,title+"_"+bmark, y_vars, plot_type=plot_type)

"""
    From a list of DataFrames, plot all data in a single plot (with legend)
    Goal: compare the results of different benchmarks (of y_vars[1]) over some predictor (y_vars[0])
"""
def plot_stacked(dfs, y_vars, plot_type="scatter"):
    total_df = pd.DataFrame()
    min_size = np.amin([len(df.index) for df in dfs])
    for df in dfs:
        relative_df = df.copy()
        relative_df[y_vars[1]] = df[y_vars[1]] / df[y_vars[1]].median()
        total_df = total_df.append(relative_df)
    total_df = total_df.pivot(index=y_vars[0], columns='Benchmark', values=y_vars[1])

    fig = plt.gcf()
    fig.set_size_inches(fig_dims)
    sns.set_style("darkgrid")

    with sns.plotting_context(font_scale=axis_scale):
        if (plot_type == "scatter"):
            ax = sns.scatterplot(data=total_df.iloc[100:200])
        else :
            ax = sns.lineplot(data=total_df.iloc[100:400])
        ax.set_xlabel(y_vars[0]+' (Random Synthesis Flow)', fontsize=axis_label, weight='bold')
        ax.set_ylabel('Relative '+y_vars[1]+' (Normalized to Median)', fontsize=axis_label, weight='bold')
        plt.legend(fontsize=legend_label,loc=1, prop={'weight': 'bold'})

    plt.savefig(y_vars[0]+'_'+y_vars[1]+'.png',  format='png', dpi=300)
    plt.close() 



def main():
    # Generate scatterplots for random runs
    # dfs = load_data_from_dir("results/random*.csv")
    # plot_singles(dfs, "random", ['Slice_LUTs', 'Path_Delay'], plot_type="scatter-ratios")
    dfs = load_data_from_dir("abc9*.csv")
    print(dfs[0])
    plot_singles(dfs, "random", ['Slice_LUTs', 'Path_Delay'], plot_type="scatter-ratios")

    # Stacked plot to compare QoRs of same scripts on different benchmarks
    # plot_stacked(dfs, ['Index', 'Path_Delay'], plot_type="scatter")
    # plot_stacked(dfs, ['Index', 'Slice_LUTs'], plot_type="scatter")

    # for df in dfs:
    #     if df.iloc[0]['Benchmark'] == "or1200":
    #         plot_single(df, "Vivado_vs_ABC", ['ABC_Delay', 'Path_Delay'], plot_type="scatter")
    #         plot_single(df, "Vivado_vs_ABC", ['ABC_Area', 'Slice_LUTs'], plot_type="scatter")
    # exh = load_data_from_dir("results/exh*.csv")
    # plot_single(exh[0], "VTR_Armcore", ['ABC_Delay', 'Path_Delay'], plot_type="scatter")
    # plot_single(exh[0], "VTR_Armcore", ['ABC_Area', 'Slice_LUTs'], plot_type="scatter")
    # plot_single(exh[0], "Exhaustive_Armcore", ['Slice_LUTs','Path_Delay'], plot_type="scatter-ratios")


if __name__ == "__main__":
    main()
