import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.style.use('ggplot')
import seaborn as sns
import pandas as pd

sns.set()


df = pd.read_csv('or1200.out.csv')
print(df.keys())
sns_plot = sns.scatterplot(df, x='PathDelay', y='LUTsLogic')
sns_plot.savefig("output.png")