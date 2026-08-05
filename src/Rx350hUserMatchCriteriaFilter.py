import pandas
import sys

# Match criteria filter for the Lexus RX 350h, the RX hybrid.
#
# Run this with VEHICLE_MAKE=lexus and MODEL=RXh   (note the LOWERCASE h, the model code is case
# sensitive and "RXH" will not work).  The RX hybrid is its own series, separate from the gas RX:
#   RX      - gas, every RX 350 trim
#   RXh     - this one, the RX 350h
#   RXphev  - the RX plug in hybrid
#   RX500h  - the RX 500h F SPORT PERFORMANCE
#
# Because RXh is already exactly the RX 350h, no trim filtering is needed to isolate the model the
# way the gas RX 350 filter has to.  A measured national run returned 1633 vehicles across only
# four trims, all of them awd, since the RX 350h does not come in front wheel drive:
#   RX 350h PREMIUM+ awd, RX 350h PREMIUM awd, RX 350h LUXURY awd, RX 350h F SPORT DESIGN awd
#
# WATCH OUT for the difference between this filter and the gas Rx350 one.  models.py sets the lexus
# title to the model code, and vehicles.py strips "<title> " off the front of the marketing name:
#   MODEL=RX   title "RX"   "RX 350 PREMIUM awd"   starts with "RX " -> becomes "350 PREMIUM awd"
#   MODEL=RXh  title "RXh"  "RX 350h PREMIUM+ awd" has no "RXh "    -> stays as it is
# So this filter still matches on the FULL name "RX 350h", while the gas RX one matches on "350".
#
# Lexus also returns the drivetrain LOWERCASE ("awd"), so str.contains("AWD") matches nothing here.
# Use "awd" or pass case=False.
#
# Adjust the price ceiling and trim below to taste.  To narrow to specific trims, add something
# like  & (df["Model"].str.contains("LUXURY|PREMIUM\\+", regex=True))

def filterDataFrame(df):
    dfFiltered = df[(df["Model"].str.contains("RX 350h", na=False))
                    & (df["Pre-Sold"] == False)
                    & (df["Hold Status"].isin(["Available", None, "", "DealerHold"]))
                    & (df["Selling Price"] <= 70000)]
    return dfFiltered

def criteriaPrintableString():
    # returns a string of the printed criteria
    criteriaStr = ""
    criteriaStr += 'Match criteria is: df[(df["Model"].str.contains("RX 350h", na=False)) & (df["Pre-Sold"] == False) & (df["Hold Status"].isin(["Available", None, "", "DealerHold"])) & (df["Selling Price"] <= 70000)]'
    return criteriaStr
