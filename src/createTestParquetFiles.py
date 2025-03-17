import pandas as pd

df = pd.read_parquet(f"output/4runnerhybrid_raw.parquet")

df.to_csv(f"output/4runnerhybridTest0_raw.csv", index=False)

df.to_parquet(f"output/4runnerhybridTest0_raw.parquet", index=False)

#pd.read_csv(f"output/4runnerhybrid.csv", index=False)

# read in 4runnerhybrid Test 0 parquet
df = pd.read_parquet(f"output/4runnerhybridTest0_raw.parquet")

# get first row
dfAdd1 = df[df.index == 0].copy()
# change vin to unique string to be in middle once sort by vin
dfAdd1.at[0,"vin"] = "JTDAAAAA3RA01Add1"
# add to df
df = pd.concat([df, dfAdd1])
# change vin to unique string to be at end once sort by vin
dfAdd1.at[0,"vin"] = "JTDAAAAAYRA01Add2"
# add to df
df = pd.concat([df, dfAdd1])
#create modified row  (change year as needed to make different than Test0 parquet and that is >= last model year )
df.at[8, "year"] = 2026
df.at[8, "eta.currFromDate"] = '2026-02-18' 
df.at[8, "eta.currToDate"] = '2026-03-18'
df.at[8, "stockNum"] = '116963'
# delete a row
df.drop(6, inplace=True)
# store df out to test1 parquet
df.sort_values("vin", inplace=True)
df.to_parquet(f"output/4runnerhybridTest1_raw.parquet", index=False)
df.to_csv(f"output/4runnerhybridTest1_raw.csv", index=False)
