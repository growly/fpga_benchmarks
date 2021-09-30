import numpy as np
import matplotlib as mpl
mpl.use('Agg')

import matplotlib.pyplot as plt
import scipy.io
from scipy import stats
import pandas as pd
import random

import plots

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
abc9_ops = aig_ind_ops + aig_ch_ops + ["&if -W 300 -K 6 -v", "&mfs", "&st", "&sweep"]

def make_hist(seq):
    hist = {key: 0 for key in abc9_ops}
    for transformation in seq:
        hist[transformation] += 1
    return hist

def onehot_final_pass(seq):
    one_hot_encoding = { ("Final_"+key): 0 for key in abc9_ops}
    one_hot_encoding["Final_"+seq[-4]] = 1
    return one_hot_encoding
    
def get_transform_hist(df, y_val):
    seqs = df['Sequence'].str.split(';')
    newdf = pd.DataFrame([make_hist(seq[1:-5]) for seq in seqs])
    newdf = pd.concat([newdf, pd.DataFrame([onehot_final_pass(seq) for seq in seqs])], axis=1)
    print(newdf)
#    newdf['Final_Pass'] = [aig_all_ops.index(seq[-4]) for  seq in  seqs]
    return newdf
                        

def feature_importances(df, y_val, params):
    X = get_transform_hist(df, y_val)
    binner = KBinsDiscretizer(n_bins=10, encode='ordinal', strategy='uniform')
    y = binner.fit_transform(df[y_val].to_numpy().reshape(len(df[y_val]), 1))
    rf = RandomForestClassifier(**params)
    #rf = RandomForestRegressor()
    
    rf.fit(X, y.reshape(len(y),))
    importances = rf.feature_importances_
    import seaborn as sns
    sns.set_style("darkgrid")
    fig = plt.gcf()
    fig.set_size_inches(12,8)
    with sns.plotting_context(font_scale=0.5):
        ax = sns.barplot(y=X.columns, x=importances)
        ax.set_xlabel("Feature Importance")
        plt.savefig("HistoryPassImportance.png", format="png", dpi=300)
        plt.close
    from sklearn.tree import plot_tree
    import graphviz
    from sklearn.tree import export_graphviz
    print(y)
    dot_data = export_graphviz(rf.estimators_[99], 
                           feature_names=X.columns,
                           filled=True, impurity=True, 
                           rounded=True)

    graph = graphviz.Source(dot_data, format='png')
    graph.render('DecisionTree0')


def run_random_forest(df, y_val):
    X = get_transform_hist(df, y_val)
    binner = KBinsDiscretizer(n_bins=10, encode='ordinal', strategy='uniform')
    y = binner.fit_transform(df[y_val].to_numpy().reshape(len(df[y_val]), 1))
    rf = RandomForestClassifier()
    #rf = RandomForestRegressor()
    param_grid = {
        'bootstrap': [True],
        'max_depth': [5, 10],
        'min_samples_leaf': [15, 20, 25, 30],
        'min_samples_split': [2, 3, 4],
        'n_estimators': [300, 350, 400, 450,500],
        'max_features':['sqrt']
    }
#    grid_rf = GridSearchCV(rf,param_grid,refit=True,verbose = 1, n_jobs=-1)
#    grid_rf.fit(X,y.reshape(len(y),))
    print("Best params:")
    params = {'bootstrap': True, 'ccp_alpha': 0.0, 'class_weight': None, 'criterion': 'gini', 'max_depth': 5, 'max_features': 'sqrt', 'max_leaf_nodes': None, 'max_samples': None, 'min_impurity_decrease': 0.0, 'min_impurity_split': None, 'min_samples_leaf': 15, 'min_samples_split': 3, 'min_weight_fraction_leaf': 0.0, 'n_estimators': 300, 'n_jobs': None, 'oob_score': False, 'random_state': None, 'verbose': 0, 'warm_start': False}
    feature_importances(df, y_val, params)  

#    print(grid_rf.best_estimator_.get_params())
#    feature_importances(df, y_val, grid_rf.best_estimator_.get_params())
    

def main():
    dfs = plots.load_data_from_dir("results/exh_*.csv")
    print(dfs[0].dropna(subset=['Path_Delay']))
#    print(get_transform_hist(dfs[0].dropna(subset=['Path_Delay']), 'Path_Delay'))
    run_random_forest(dfs[0].dropna(subset=['Path_Delay']), 'Path_Delay') 
#    run_random_forest(dfs[0].dropna(subset=['Path_Delay']), 'Path_Delay')

if __name__ == "__main__":
    main()
