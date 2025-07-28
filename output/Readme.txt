Readme.txt updated 7/25/2025  (version history for Readme.txt at https://github.com/ghgemmer/yotagrabber/blob/main/output/Readme.txt)
Alert!!!!  7/25/2025.  My Internet Service Provider has been down since 7/23/2025 so I have not been able to 
run the inventory program.  Looks like I won't have internet service until 7/28/2025 at earliest.  Arggghhhh

This folder contains the new/allocated inventory for all Toyota vehicle models in the US, including Alaska, but currently excluding Hawaii.
The inventory is obtained from the same place the Toyota Inventory search website (https://www.toyota.com/search-inventory/)
gets its data from (which is https://api.search-inventory.toyota.com/graphql ).  The folder also contains the sold inventory 
(inventory that appeard at one time in a run, but no longer appears in the inventory obtained from the website), as well as Change History 
event files for the last 14 days which contain added VINs, modified contents of existing VINs, or removed VINs between runs of the inventory 
collection over that time period.

All files are read only view on my google drive.  Thus if you wish to do filtering, etc you need 
download the file and open it or save it to your own google drive.

Folder updates typically show up each day around 5am CDT.
Each model's current inventory is placed in a <model>.csv file.  A raw  (filename <model>_Lastraw.parquet)
python pandas parquet file is also created which is the raw inventory obtained from the Toyota website for the model
before various filtering/modification is applied for the csv file, such as removal of many fields we don't use or 
want to show in the .csv file, some field names and content are modified for readability,  etc. 
There is also a <model>_LastStatusInfo.json file  associated
with the raw parquet file that indicates status details of the obtained raw inventory which are: 
did the inventory get work (got valid inventory responses although may be missing some vehicles),  
how many vehicles found, how many vehicles were missing, date and time of the get.
Note that the .parquet and .csv file also include an infoDateTime column which indicates when the information for
that row was updated from the toyota website, as well as a FirstAddedDate for the date the VIN first appeared in 
the inventory (or reappeared after disappearing), and a LastChangedDateTime which indicates the last date and time 
any information for that VIN changed.

The sold inventory files are for VINs that no longer appear in the current inventory (were seen at one time 
by the inventory run but have since disappered).
These files are named  <model>_<year>_Sold.csv with the associated raw parquet in <model>_<year>_Sold_raw.parquet
Also note that currently if a temp VIN is turned into a real VIN, and thus the temp VIN disappears, 
the temp VIN is treated as Sold, because it disappeared from current inventory, and is placed in the associated Sold file. 
This currently allows temp VINs to still be seen for a period of time and a user to
know when it was turned into a real VIN by the infoDateTime field (not necessarily what the real VIN is).
A user can determine the real VIN that has replaced a temp VIN by using the Change History file (see below).
Once a temp VIN in the sold file is older than 16 weeks it is assumed it has been replaced with a real VIN 
and/or the user no longer needs use of the temp VIN, and it is removed from the sold files.  This period of
time also allows some statistics to be run on the day of the month allocations appear.
Older model year sold files will be archived at some point, when it appears there is no longer any inventory of that year left.

Note that the contents of the VIN entries in the sold inventory files do not update after being placed in that file because there is no data 
to update them with from the Toyota search inventory website anymore. I.E, the website no longer returns that VIN and contents for it,
and that is the only website that the vehicle information is obtained from by the program.

Change History events are in the  <model>_ChangeHistory.csv and .parquet files.
They contains all changes between runs of the inventory collection,
which are any added (new or reappeared) VINs, modified contents of existing VINs, or removed VINs. 
This allows a user to see the changes that occurred from run to run.
Only the last 14 days of changes are kept.
A typical use of this file is to watch for changes to the column values of a specific VIN  (sort by VIN and find the specific
VIN).  The user can visually scan for changes between values in the rows for that VIN or look at the
List of Changes column (for change types of MODED) to see a concise list only the changes that occured between the current row
and the previous row.

A user would typically note the last time they viewed that VIN info in this file and then be sure to 
view the file at least every 14 days to see all changes to the column values for that VIN after the last time it
was viewed.

Additional columns in these Change History files, which are described later on below, are as follows:
RowChangeType, 
Event DateTime,
List of Changes

A user can determine, with reasonable certainty, the real VIN that has replaced a temp VIN by using the Change History file,
assuming this is done before 14 days after the temp VIN disappeared from the inventory.
Open the Change History .csv file in Excel and sort ascending by "Dealer Website".  
Insert a blank column to the right of the "isTempVin" column.
Turn on data filtering.
Add the following formula to row 2 of that new blank column
=OR(AND(S2=FALSE, S3=TRUE,U2=U3, A2="ADDED", A3="REMOVED", B2=B3,I2=I3, AS2=AS3), AND(S1=FALSE, S2=TRUE,U1=U2, A1="ADDED", A2="REMOVED", B1=B2, I1=I2, AS1=AS2))
then copy and paste that cell to all the other cells below in that column
Now filter on the value TRUE for that new column.
You should see pairs of rows, were each pair is ADDED followed by REMOVED. The ADDED one contains the real VIN 
and the REMVOED contains the temp VIN and all the other columns should match between the two (excluding obvious ones that
will be different).  The above formula doesn't check that all columns match, just that the Selling Price, Options and
Event DateTime match between the columns which in general if they do then the others probably match as well, but you 
need to visually verify the other columns just to make sure.


A log file InventoryRunlog.txt is also provided which indicates when the inventory search started, log of
progress on getting each model (graphql inventory page number on , number of pages, number of records, i.e. vehicles, 
any error messages or retries) as well as if the program could not find all the inventory for a given model and how many 
vehicles were missing for that model in that case. Note that as each page of vehicle inventory is gotten for a given
model, the total records (total number of vehicles for that model that will be returned over the total number
of pages indicated for that model ) the website returns can change on the fly.  So sometimes when we get close
to the end of the inventory pages for a model, we may miss a few just newly added vehicles.  These will then
show up the next time the inventory search is run. The InventoryRunlog may also contain several days runs so
the latest is at the bottom of the file.


Column definitions that are not obvious or to remove any ambiguity are as follows:
"Model" -  This actually contains just the Trim + Drivetrain code (for example XLE FWD, TRD Sport RWD, SR5 4WD).
           The top level model name is left off (Camry, 4Runner, etc) as the file name implies it.
"Color" - Exterior color
"Int Color" - Interior color
"Base MSRP" -  Is as shown on the cars window sticker and is the Base manufacturer retail price 
"Total MSRP" -  Also referred to as the Total SRP (Suggested Retail Price) as shown on the cars window sticker is the 
                Base MSRP + all the factory and Port installed options/packages + delivery/handling fees  
                (excludes taxes and other fees like Doc fee, registration fees, etc)
"Selling Price" -  is the total dealer price (excluding taxes, fees) = Total MSRP + Dealer installed options + Dealer Markup/Discount/adjustments
                   It is the bottom line final price the Toyota Search Inventory website shows with the exeptions indicated below.
                   Note that this value in general matches the dealer website value but can be different if the dealer website 
                   has additional adjustments it does not reflect back to the Toyota Search Inventory database or has not correctly updated those
                   values in the database. 
                   This is calculated logically equivalent to what the Toyota Search Inventory website Java Script code does with the noted exceptions. 
                   The logic used for calculating the Selling Price is as follows:
                   sellingPriceIncomplete = False
                   if sellingPrice is present and (sellingPrice >= 10000):
                       # selling price ok as is
                   else:
                       if isSmartPathPresentAndTrue:
                           if advertizedPrice is present:
                               sellingPrice = advertizedPrice
                           else:
                               sellingPrice = 0
                       else:
                           if nonSpAdvertizedPrice is present:
                               sellingPrice = nonSpAdvertizedPrice
                           else:
                               sellingPrice = 0
                       if sellingPrice is present and (sellingPrice >= 10000):
                           # selling price ok as is
                       else:
                           if tMsrpPlusDio is present and (tMsrpPlusDio >= 10000): # (!!!!The actual website java script code uses the Total MSRP column instead.  Decided to use the TMSRP plus DIO to show worst case price)
                               sellingPriceIncomplete = True
                               sellingPrice = tMsrpPlusDio
                           else:
                               sellingPriceIncomplete = True
                               sellingPrice = totalMsrp
                               
"Selling Price Incomplete" - Indicates if the Selling Price is incomplete. When incomplete the price 
                             does not include the Dealer Markup/Discount as it was unknown.
"Markup" - Dealer installed options plus Dealer Markup/Discount/adjustments (i.e everything above the Total MSRP to get to the Selling Price)
"TMSRP plus DIO" -  Total MSRP plus Dealer installed options.  This is calculated as "Total MSRP" + price.dioTotalDealerSellingPrice if present 
                otherwise just "Total MSRP".  This is based on observation from dealer websites so may not be exactly correct in all cases.
"Hold Status" - There is uncertainty as to what exactly this field indicates. One opinion is it 
                indicates the degree to which that vehicle is available/spoken for.  Generally, when looking for a vehicle,
                you want to first contact dealers where PreSold is False and the hold status is blank , then those where it is "Available",  
                then lastly where it is "Dealer hold".
                In this interpretation "Dealer hold" means the vehicle is spoken for already, and Available or blank means it is not.
                Another opinion is hold status indicates whether a dealer would offer the vehicle to another dealer for a swap or sale.
                In this intepretation "Dealer hold" indicates the vehicle will not be offered to other dealers
                for swapping or sale (which, among other reasons, might possibly be because it is in high demand or being held for someone or there is a waiting list for it)
                ,  and blank of Available indicates they would.
                
"Pre-Sold" - The vehicle sale is pending or considered sold for all practical purposes.
                .
"Shipping Status" - "Factory to port" -  Allocated, or in production, or on the ship, or sitting at the port
                    "Port to dealer" -  Checked in at the port and in the process of moving from the port to the dealership lot.
                    Usually From and To Date will now appear.
                    "At dealer" - The car is at the dealer
                    The above "Shipping Status" defintions were copied and pasted from another developers spreadsheet
"eta.currFromDate" - Estimate To Arrival at dealer earliest date estimate.
"eta.currToDate" -   Estimate To Arrival at dealer latest date estimate.
"FirstAddedDate" - Date and time the VIN first appeared in inventory retrieved from the website (or reappeared after disappearing).
"LastChangedDateTime" -  Indicates the last date and time any column information for that VIN changed. Note that when a new VIN
                         is added the LastChangedDateTime is set to the FirstAddedDate.
                         LastChangedDateTime can be used to know if anything has changed in the row for that VIN since a certain date.
                         Thus a user can simply remember the last time the VIN row info was viewed and then just look at the 
                         LastChangedDateTime to know if anything has changed since then.  At that point the user can then scan the
                         row visually to see what changed or go to the Change History file, assuming the change
                         occurred in the last 14 days,  to get an exact list of what changed.
"infoDateTime" -  Date and time that the row was updated from the inventory website.
"Dealer Lat" -  Dealer Latitude
"Dealer Long" - Dealer Longitude.  
"CenterLat" -  Latitude of a user desired Center location. User manually fills in this desired location in the spreadsheet
               opened in Excel and uses the same value for each cell in this column.  Only needed if user want to do distance
               calculations.
"CenterLong" - Longitude of a user desired Center location. User manually fills in this desired location in the spreadsheet
               opened in Excel and uses the same value for each cell in this column. Only needed if user want to do distance
               calculations.
"DistanceFromCenter" -  The distance from the Center location to the Dealer location in miles (straight line).
                        Only the first cell in this column is filled in with the Excel formula that calculates this distance
                        using the Dealer Lat, Long, and Center Lat, Long values in the row.  The following is only needed
                        if the user desires to calculate this distance for all rows in the spreadsheet.
                        The user must then Excel copy and paste this cell to all the other cells in this column in Excel
                        to get the calculated distance from Center location to Dealer location for each row.
                        Only the first cell formula is supplied so that the .csv file size remains reasonably small.
                        The Excel spreadsheet can be saved to a .xlsx file if desired to retain this.
                        The CenterLat and CenterLong columns can be updated as desired and the calculated distance automatically
                        shows up then.
                        The formula for the distance is the Haversine formula which is as follows:
                        =ACOS(COS(RADIANS(90-DealerLat))*COS(RADIANS(90-CenterLat))+SIN(RADIANS(90-DealerLat))*SIN(RADIANS(90-CenterLat))*COS(RADIANS(DealerLong-CenterLong)))*6371*0.621371


Additional columns in the Change History files are:
"RowChangeType"  - Indicates if this VIN row was an ADDED, MODED, or REMOVED row from the prior inventory run.
                   For MODED rows any changes between the old data and the new data of any column for that row
                   are in the "List of Changes" column.
                    
"Event DateTime" - The datetime that the Change was determined on.  For a given inventory run for a given model
                   these are all the same date and time for all the events added during that inventory run.
                   
"List of Changes" - A list of the names of only the columns for that row that changed value and the old and new value.  
                    Options are handled by showing all the options which were added, followed by all those removed, followed by
                    all those that stayed the same.  Column names and Options are sorted, case insensitive , ascending order
                    to make it easier to find out if a given column or option changed.

Note that sometimes a "Dealer State" column cell may be blank.  I will automatically be alerted of this and this will be 
corrected typically within a day or two. This is because the dealer state information is currently maintained in a separate
database and changes only infrequently, so is not dynamically extracted from the website when the inventory is extracted
to reduce the time it takes to get the inventory.

For issues or questions contact ghgemmer@gmail.com
See github repository https://github.com/ghgemmer/yotagrabber
for the source code for this forked project.

That project also added a higher level search program searchForVehicles.py that can notify the user via any
combination of sound, email, text whenever changes in the inventory data occur for a specified match criteria.
This allows a user to be alerted whenever what they are looking for has changed and then look at the attached
log file to view the changes.  That program uses a config YAML file that can specify how often to search, the
match filter criteria filename, sound file options, texting options, email options, how changes are reported,
log file options, etc. See SearchVehicles-Example_config.yaml for all the configuration items that can be set

searchForVehicles.py runs the vehicles.py update_vehicles() method to collect an inventory of all vehicles in
the US for a desired model , or all vehicles within a specified distance from a specified zip code for that
model (limited to 10,000 vehicles at most when specify zipcode), and then runs a specified user match criteria against that 
looking for specific vehicles.  Whenever any inventory changes occur for that match criteria the program notifies the user via 
any user specified combination of sound, email, text.

