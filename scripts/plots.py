import numpy as np
import matplotlib as mpl
mpl.use('Agg')

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import glob, os.path, os

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
        dfs.append(data)
    return dfs

    

def scatterplot_seaborn_single(df, title):
    sns.set_style("darkgrid")
    ax = sns.scatterplot(x='Index', y ='PathDelay',  data=df);
    plt.title(title)
    plt.savefig(title+'index_pathdelay.png',  format='png', dpi=300)
    plt.close() 

def scatterplot_seaborn(dfs, title):
    df = pd.DataFrame()
    for this_df in dfs:
        df = df.append(this_df)
    print(df)
    sns.set_style("darkgrid")
    ax = sns.scatterplot(x='Index', y ='PathDelay',  data=dfs, hue="Benchmark", time="Benchmark");
    plt.title(title)
    plt.savefig(title+'index_pathdelay.png',  format='png', dpi=300)
    plt.close() 

def plot_q2(q2_dfs, bmark):
    q2_df = pd.DataFrame()
    for df in q2_dfs:
        q2_df = q2_df.append(df)

    if bmark == "Hopper":
        bc_baseline = q1_hopper_dfs[1].loc[0, 'Eval_AverageReturn']
    else:
        bc_baseline = q1_ant_dfs[1].loc[0,'Eval_AverageReturn']
        
    expert_baseline = q2_df.iloc[0].loc['Initial_DataCollection_AverageReturn']

    q2_df = q2_df.sort_values(by=['Dagger_Itreations'])
    # PART 2
    sns.set_style("darkgrid")
    color='steelblue' if bmark == "Hopper" else 'coral'

    
    ax = sns.pointplot(x='Dagger_Itreations', y ='Eval_AverageReturn', color=color, data=q2_df, dodge=True, join=False);
    bottom, top = plt.ylim() 
    # plt.ylim(bottom, expert_baseline + 1000)
    ax.axhline(bc_baseline, ls='--', color='red')
    ax.text(2,bc_baseline + (top-bottom)//20, "BC Agent")

    ax.axhline(expert_baseline, ls='-.', color='black')
    ax.text(4,expert_baseline- (top-bottom)//10, "Expert Policy")
    # Find the x,y coordinates for each point
    x_coords = []
    y_coords = []
    for point_pair in ax.collections:
        for x, y in point_pair.get_offsets():
            x_coords.append(x)
            y_coords.append(y)

    # Calculate the type of error to plot as the error bars
    # Make sure the order is the same as the points were looped over
    ax.errorbar(x_coords, y_coords, yerr=q2_df['Eval_StdReturn'], ecolor=color, fmt=' ', zorder=-1)
    plt.title(bmark)
    plt.savefig('q2_{}.png'.format(bmark),  format='png', dpi=300)
    plt.savefig('q2_{}.eps'.format(bmark),  format='eps')
    plt.close() 


def main():
    df, tag = load_data("results/random_or1200.out.csv")
    scatterplot_seaborn_single(df,tag)
    dfs = load_data_from_dir("results/random*.csv")
    scatterplot_seaborn(dfs, "Random Iterations")
if __name__ == "__main__":
    main()