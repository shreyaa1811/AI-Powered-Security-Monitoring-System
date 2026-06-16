import pandas as pd

normal_df = pd.read_csv("data/normal_logs.csv")
attack_df = pd.read_csv("data/attack_logs.csv")

all_logs = pd.concat([normal_df,attack_df],ignore_index=True)
all_logs.to_csv("data/combined_logs.csv",index=False)

print("All logs combined : ",all_logs.shape)
