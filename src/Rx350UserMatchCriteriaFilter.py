import pandas
import sys

# Match criteria filter for the Lexus RX 350.
#
# Run this with VEHICLE_MAKE=lexus and MODEL=RX.  RX 350 is not a model code of its own, it is a
# trim inside the RX series, so the inventory pulled for the RX series contains every RX 350 trim
# (RX 350 PREMIUM, RX 350 PREMIUM+, RX 350 LUXURY, RX 350 F SPORT HANDLING, ...) and this filter
# narrows it to the ones wanted.  The hybrids are separate model codes (RXH for the RX 350h and
# RX500H for the RX 500h), so they never show up in an RX search and do not need excluding here.
#
# Note that the Model column has the series name stripped off the front, the same way toyota's is,
# because models.py sets the lexus title to the model code.  So with MODEL=RX the leading "RX " is
# removed and the column holds the trim plus the drivetrain, for example "350 LUXURY fwd" or
# "350 F SPORT HANDLING awd".  That is why the pattern below is "350" and not "RX 350".
#
# WATCH THE CASE on the drivetrain: lexus returns it LOWERCASE ("awd", "fwd"), unlike toyota which
# returns "4x4" / "AWD".  So filtering with str.contains("AWD") matches nothing here.  Use
# str.contains("awd") or pass case=False.  Trim names are uppercase (PREMIUM, PREMIUM+, LUXURY,
# F SPORT DESIGN, F SPORT HANDLING, and a bare "RX 350" for the base trim).
#
# Adjust the price ceiling, drivetrain and trim to taste.  Everything below the first condition is
# optional, so delete what does not apply.

    # The "350(?!h)" pattern rejects a "350h" that contains "350" as a substring.  An RX
    # search never returns hybrids anyway, so this only matters if this filter is ever pointed at a
    # combined data set.

def filterDataFrame(df):
    dfFiltered = df[(df["Model"].str.contains(r"^350(?!h)", na=False, regex=True))
                    & (df["Pre-Sold"] == False)
                    & (df["Hold Status"].isin(["Available", None, "", "DealerHold"]))
                    & (df["Selling Price"] <= 65000)]
    return dfFiltered

def criteriaPrintableString():
    # returns a string of the printed criteria
    criteriaStr = ""
    criteriaStr += 'Match criteria is: df[(df["Model"].str.contains(r"^350(?!h)", na=False, regex=True)) & (df["Pre-Sold"] == False) & (df["Hold Status"].isin(["Available", None, "", "DealerHold"])) & (df["Selling Price"] <= 65000)]'
    return criteriaStr
