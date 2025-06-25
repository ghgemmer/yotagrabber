import pandas
import sys

def filterDataFrame(df):
    dfFiltered = df[(df["VIN"] != "JTEVB5BR0S111BE87")  |  (df["Selling Price"] < 70000)]
    return dfFiltered
    
def criteriaPrintableString():
    # returns a string of the printed criteria
    criteriaStr = ""
    criteriaStr += 'Match criteria is df[(df["VIN"] != "JTEVB5BR0S111BE87")  |  (df["Selling Price"] < 70000)]'
    return criteriaStr
