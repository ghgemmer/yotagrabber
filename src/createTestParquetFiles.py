import pandas as pd
import json

##df = pd.read_parquet(f"output/4runnerhybrid_raw.parquet")

#df.to_csv(f"output/4runnerhybridTest0_raw.csv", index=False)

#df.to_parquet(f"output/4runnerhybridTest0_raw.parquet", index=False)

#pd.read_csv(f"output/4runnerhybrid.csv", index=False)

# read in 4runnerhybrid Test 0 parquet
df = pd.read_parquet(f"output/4runnerhybridTest0_raw.parquet")
df = df.reset_index(drop=True)

# limit to 100 entries
df = df[df.index < 100]
# change year so that vehicles.py doesn't drop it as it requires model year  >= current year -1 
df["year"] = 2050
df.to_parquet(f"output/4runnerhybridTest0_raw.parquet", index=False)
# create json status file for it
dfTestStatus = {
    "completedOk": True,
    "numberRawVehiclesFound": len(df),
    "numberRawVehiclesMissing": 0,
    "completionMsg": "",
    "date": "2050-03-17 10:49:24.252453"
}
with open(f"output/4runnerhybridTest0_StatusInfo.json", "w") as f:
    json.dump(dfTestStatus, f, indent=4)

# create half empty version of that parquet by only keeping the first 50 entries
dfHalfEmpty = df[df.index < 50]
dfHalfEmpty.to_parquet(f"output/4runnerhybridTest3HalfEmpty_raw.parquet", index=False)
# create json status file for it
dfTestStatus = {
    "completedOk": True,
    "numberRawVehiclesFound": len(dfHalfEmpty),
    "numberRawVehiclesMissing": 0,
    "completionMsg": "",
    "date": "2050-03-17 10:49:24.252453"
}
with open(f"output/4runnerhybridTest3HalfEmpty_StatusInfo.json", "w") as f:
    json.dump(dfTestStatus, f, indent=4)

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
df.at[8, "year"] = 2051
df.at[8, "eta.currFromDate"] = '2051-02-18' 
df.at[8, "eta.currToDate"] = '2051-03-18'
df.at[8, "stockNum"] = '116963'
# delete a row
df.drop(6, inplace=True)
# store df out to test1 parquet
df.sort_values("vin", inplace=True)
df.to_parquet(f"output/4runnerhybridTest1_raw.parquet", index=False)
# create json status file for it
dfTestStatus = {
    "completedOk": True,
    "numberRawVehiclesFound": len(df),
    "numberRawVehiclesMissing": 0,
    "completionMsg": "",
    "date": "2051-03-17 10:49:24.252453"
}
with open(f"output/4runnerhybridTest1_StatusInfo.json", "w") as f:
    json.dump(dfTestStatus, f, indent=4)
    
df.to_csv(f"output/4runnerhybridTest1_raw.csv", index=False)
