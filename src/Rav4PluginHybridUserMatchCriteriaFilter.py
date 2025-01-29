import pandas
import sys

def filterDataFrame(df):
    dfFiltered = df[(df["Model"].str.contains("XSE")) & (df["Pre-Sold"] == False) & (df["Hold Status"].isin(["Available", None, "", "DealerHold"])) & (df["Selling Price"] <= (52045 + 1650)) & ( df["Options"].str.contains("Premium Package") & df["Options"].str.contains("Weather Package"))]
    return dfFiltered
    
def criteriaPrintableString():
    # returns a string of the printed criteria
    criteriaStr = ""
    criteriaStr += 'Match criteria is: df[(df["Model"].str.contains("XSE")) & (df["Pre-Sold"] == False) & (df["Hold Status"].isin(["Available", None, "", "DealerHold"])) & (df["Selling Price"] <= (52045 + 1650)) & ( df["Options"].str.contains("Premium Package") & df["Options"].str.contains("Weather Package"))]'
    return criteriaStr
