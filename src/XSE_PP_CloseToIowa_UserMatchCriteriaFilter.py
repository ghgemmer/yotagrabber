import pandas
import sys

def filterDataFrame(df):
    dfFiltered = df[(df["Model"].str.contains("XSE")) & (df["Pre-Sold"] == False) & (df["Hold Status"].isin(["Available", None, "", "DealerHold"])) & ((df["Selling Price"] <= (df["Total MSRP"] + 1000)) ) & (df["Dealer State"].isin(["IA", "IL", "IN", "MO", "WI", "MN", "KS", "NE", "ND"])) & ( df["Options"].str.contains("Premium Package") & df["Options"].str.contains("Weather Package"))]
    return dfFiltered
    
def criteriaPrintableString():
    # returns a string of the printed criteria
    criteriaStr = ""
    criteriaStr += 'Match criteria is: df[(df["Model"].str.contains("XSE")) & (df["Pre-Sold"] == False) & (df["Hold Status"].isin(["Available", None, "", "DealerHold"])) & ((df["Selling Price"] <= (df["Total MSRP"] + 1000)) ) & (df["Dealer State"].isin(["IA", "IL", "IN", "MO", "WI", "MN", "KS", "NE", "ND"])) & ( df["Options"].str.contains("Premium Package") & df["Options"].str.contains("Weather Package"))]'
    return criteriaStr
