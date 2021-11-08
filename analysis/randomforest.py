import numpy as np
import matplotlib as mpl
mpl.use('Agg')

import matplotlib.pyplot as plt
import scipy.io
from scipy import stats
import pandas as pd
import random
import seaborn as sns
import plots

fig_dims = (20,16)
axis_label = 12
legend_label = 12
axis_scale = 0.5

from sklearn.tree import DecisionTreeClassifier, export_graphviz
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.decomposition import PCA
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, KBinsDiscretizer
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV, train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

random.seed(1)
np.random.seed(1)

aig_ind_ops = ["&dc2", "&syn2", "&syn3", "&syn4", "&b", "&b -d",
               "&if -W 300 -x -K 6", "&if -W 300 -g -K 6", "&if -W 300 -y -K 6"]
aig_ch_ops = ["&synch2", "&dch", "&dch -f"]
abc9_ops = aig_ind_ops + aig_ch_ops + ["&if -W 300 -K 6 -v", "&mfs", "&st"]

labels_abc9_ops = ["&dc2", "&syn2", "&syn3", "&syn4", "&b", "&b -d", "&if -x", "&if -g", "&if -y", "&synch2", "&dch", "&dch -f", "&if", "&mfs", "&st"]
final_passes = ["&dc2", "&syn2", "&syn3", "&syn4", "&b", "&b -d", "&if -x", "&if -g", "&if -y", "&synch2", "&dch -f", "&dch","&st"]

bmark_baseline_delays={"armcore":24.612, "bgm_original": 17.834}
def make_hist(seq):
    hist = {key: 0 for key in abc9_ops}
    if len(seq) > 1 :
        for transformation in seq:
            hist[transformation] += 1
    return hist

def onehot_final_pass(seq):
    one_hot_encoding = { ("Final_"+key): 0 for key in abc9_ops}
    one_hot_encoding["Final_"+seq[-4]] = 1
    return one_hot_encoding
    
# def get_transform_hist(df, y_val):
#     newdf = pd.DataFrame(make_hist(df['Previous'])
#     newdf = pd.concat([newdf, pd.DataFrame([onehot_final_pass(seq) for seq in newdf['']])], axis=1)
#     print(newdf)
# #    newdf['Final_Pass'] = [aig_all_ops.index(seq[-4]) for  seq in  seqs]
#     return newdf

'''
Transform exhaustive search result dataframe (list of passes, QoR metric) to 
dataframe of (previous passes, last pass, +/- in QoR metric)
'''                    
def to_relative_impact(df, y_val):
    # dfcopy = df.copy()
    df = df.copy()
    long_seqs = df['Sequence'].str.split(';')
    df['Sequence'] = [ seq[2:-3] for seq in long_seqs.copy()]
    df['Previous'] = [ seq[2:-4] for seq in long_seqs.copy()]
    df['Final_Pass'] = [ seq[-4] for seq in long_seqs.copy()]

    improvements = []
    values = df[y_val].values
    previous = df['Previous'].values
    seqs = df['Sequence'].values
    assert len(values) == len(seqs) == len(previous)
    improvements = np.zeros(len(values))
    values = df[y_val].values
    previous = df['Previous'].values
    seqs = df['Sequence'].values

    baseline = bmark_baseline_delays[df.loc[0, "Benchmark"]]
    for i in range(len(values)):
        for j in range(len(values)):
            if len(previous[i]) < 2 : 
                improvements[i] = baseline - values[i]
            elif previous[i] == seqs[j]: 
                improvements[i] = values[j] - values[i] 
    df['Improvement'] = improvements
    return df


# def plot_feature_importances(df, y_val, params):
#     X = get_transform_hist(df, y_val)
#     binner = KBinsDiscretizer(n_bins=10, encode='ordinal', strategy='uniform')
#     y = binner.fit_transform(df[y_val].to_numpy().reshape(len(df[y_val]), 1))
#     rf = RandomForestClassifier(**params)

#     # rf.fit(X, y.reshape(len(y),))
#     importances = rf.feature_importances_

#     sns.set_style("darkgrid")
#     fig = plt.gcf()
#     fig.set_size_inches(12,8)
#     with sns.plotting_context(font_scale=0.5):
#         ax = sns.barplot(y=X.columns, x=importances)
#         ax.set_xlabel("Feature Importance")
#         plt.savefig("HistoryPassImportance.png", format="png", dpi=300)
#         plt.close
#     from sklearn.tree import plot_tree
#     import graphviz
#     from sklearn.tree import export_graphviz
#     print(y)
#     dot_data = export_graphviz(rf.estimators_[99], 
#                            feature_names=X.columns,
#                            filled=True, impurity=True, 
#                            rounded=True)

#     graph = graphviz.Source(dot_data, format='png')
#     graph.render('DecisionTree0')


def run_random_forest(df):
    X = []
    for p in abc9_ops:
        subset = df.loc[df['Final_Pass'] == p]
        if subset.empty:
            continue
        # x = pd.DataFrame([make_hist(seq) for seq in subset['Previous']])
        # y = np.sign(subset['Improvement'])
        # rf = RandomForestClassifier(max_depth=3, random_state=0, n_estimators=15)
        # rf.fit(x.values,y.values)
        X.append(rf_grid_search(subset))
    
    # print([len(df.loc[df['Final_Pass'] == p]) for p in abc9_ops])
    # print(len(df.loc[df['Final_Pass'] == "&st"]))

    sns.set_style("darkgrid")
    fig = plt.gcf()
    fig.set_size_inches(12,8)
    with sns.plotting_context(font_scale=axis_scale):
        #ax = sns.barplot(y=X.columns, x=importances)
        ax = sns.heatmap(X, xticklabels=labels_abc9_ops, yticklabels=final_passes, cmap='coolwarm')
        ax.set_xlabel('Histogram of Previous Passes', fontsize=axis_label, weight='bold')
        ax.set_ylabel('Final Pass', fontsize=axis_label, weight='bold')
        plt.savefig(dfs[0].loc[0, "Benchmark"]+"_HistoryPassImportance.png", format="png", dpi=300)
        plt.close

def rf_grid_search(subset):
    rf = RandomForestClassifier()
    param_grid = {
        'bootstrap': [True],
        'max_depth': [5, 10, 12, 15],
        'min_samples_leaf': [10, 15, 20],
        'min_samples_split': [2, 3, 4],
        'n_estimators': [10, 12, 15, 20],
        'max_features':['sqrt']
    }
    # grid search setup
    #subset = df.loc[df['Final_Pass'] == '&dc2']
    grid_rf = GridSearchCV(rf, param_grid,refit=True,verbose = 1, n_jobs=-1)
    X = pd.DataFrame([make_hist(seq) for seq in subset['Previous']])
    y = np.sign(subset['Improvement'])
    grid_rf.fit(X,y)
    # print("Best params:")
    # print(grid_rf.best_estimator_.get_params())    # plot_feature_importances(df, y_val, params)  
    print(grid_rf.best_score_)
    rf = RandomForestClassifier(**grid_rf.best_estimator_.get_params())
    rf.fit(X,y)
    # print(rf.feature_importances_)
    return rf.feature_importances_


def main():
    dfs = plots.load_data_from_dir("results/exh*.csv")
    proc_df = to_relative_impact(dfs[0].dropna(subset=['Path_Delay']), 'Path_Delay')
    #proc_df = to_relative_impact(dfs[0], 'Path_Delay')

    run_random_forest(proc_df)

    # proc_dfs = plots.load_data_from_dir("results/processed_*.csv")
    # proc_df = proc_dfs[0]

    # proc_df['Sequence'] = [ ast.literal_eval(seq) for seq in proc_df.copy()['Sequence']]
    # proc_df['Previous'] = [ ast.literal_eval(seq) for seq in proc_df.copy()['Previous']]
    # run_random_forest(proc_df, 'Path_Delay') 

if __name__ == "__main__":
    main()
