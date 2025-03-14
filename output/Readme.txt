This folder contains the inventory for all Toyota vehicle models in the US (including Alaska, but currently excluding Hawaii).
The inventory is obtained from the same place the Toyota Inventory search (https://www.toyota.com/search-inventory/)
gets its data.  Only the current and prior model year of production inventory are extracted.
No history is kept, so the files contain only what that inventory website showed at the time it was accessed.

Folder updates typically show up each day around 5am CDT. Each model's inventory is placed in a .csv file.  A raw
pandas parquet file is also created which is the raw inventory obtained from the Toyota website for the model
before various fitlering is applied, such as only current and prior model years, certain fields are removed,
some field names and content are modified for readability, etc. There is also a <model>_StatusInfo.json file  associated
with the raw parquet file that indicates status details of the obtained raw inventory which are: 
did the get work (got some valid responses although may be missing some vehicles),  
how many vehicles found, how many vehicles were missing, date and time of the get.
Note that the .parquet and .csv file also include an infoDateTime column which indicates when the information for
that row was updated from the toyota website.

These files are read only view on my google drive.  Thus if you wish to do filtering, etc you need to either 
download the file and open it to do,  or click on the file's More Actions --> Open With --> Excel Desktop.

A log file InventoryRunlog.txt is also provided which indicates when the inventory search started, log of
progress on getting each model (page number on , number of pages, number of records, any error messages or
retries) as well as if the program could not find all the inventory for a given model and how many vehicles
were missing for that model in that case. Note that as each page of vehicle inventory is gotten for a given
model, the total records (total number of vehicles for that model that will be returned over the total number
of pages indicated for that model ) the website returns can change on the fly.  So sometimes when we get close
to the end of the inventory pages for a model, we may miss a few just newly added vehicles.  These will then
show up the next time the inventory search is run. The InventoryRunlog may also contain several days runs so
the latest is at the bottom of the file.


Column definitions that are not obvious or to remove any ambiguity are as follows:
"Base MSRP" -  Is as shown on the cars window sticker and is the Base manufacturer retail price 
"Total MSRP" -  Also referred to as the Total SRP (Suggested Retail Price) as shown on the cars window sticker is the 
                Base MSRP + all the factory and Port installed options/packages + delivery/handling fees  
                (excludes taxes and other fees like Doc fee, registration fees, etc)
"Selling Price" -  is the total dealer price (excluding taxes, fees) = Total MSRP + Dealer installed options + Dealer Markup/Discount/adjustments
                   It is the bottom line final price the dealers show on their website.
                   Note: This is calculated from the several raw prices the toyota graphql website returns and was arrived at 
                   by comparing those to the dealer websites final price numbers listed for many vehicles.
                   
"Selling Price Incomplete" - Indicates if the Selling Price is incomplete. When incomplete the price 
                             does not include the Dealer Markup/Discount as it was unknown.
"Markup" - Dealer installed options plus Dealer Markup/Discount/adjustments (i.e everything above the Total MSRP to get to the Selling Price)
"TMSRP plus DIO" -  Total MSRP plus Dealer installed options
"Shipping Status" - "Factory to port" -  Allocated, or in production, or on the ship, or sitting at the port
                    "Port to dealer" -  Checked in at the port and in the process of moving from the port to the dealership lot.
                    Usually From and To Date will now appear.
                    "At dealer" - The car is at the dealer
                    The above "Shipping Status" defintions were copied and pasted from another developers spreadsheet
"infoDateTime" -  the date and time that the row was updated from the toyota website.
"Dealer Lat" -  Dealer Latitude
"Dealer Long" - Dealer Longitude.  The Dealer Lat and Long can be used to calculate distance from a given Center latitude and longitude.
                The user can then filter on this for say a distance <= X miles from the Center.
                The formula for calculating the distance in miles is
                =ACOS(COS(RADIANS(90-DealerLat))*COS(RADIANS(90-CenterLat))+SIN(RADIANS(90-DealerLat))*SIN(RADIANS(90-CenterLat))*COS(RADIANS(DealerLong-CenterLong)))*6371*0.621371
                if DealerLat is in cell A1, DealerLong in cell B1,  CenterLat in cell C1, and CenterLong in cell D1 then the 
                excel formula in cell E1 to calculate the distance is 
                =ACOS(COS(RADIANS(90-A1))*COS(RADIANS(90-C1))+SIN(RADIANS(90-A1))*SIN(RADIANS(90-C1))*COS(RADIANS(B1-D1)))*6371*0.621371
                Thus a CenterLat and Long columns can be added after the DealerLong column and filled with a fixed value
                you want to find the distance from
                and then a distance column added after that and then the above cell E1 in another sheet can be copied
                and pasted to all cells in the distance column
 
Note that sometimes a "Dealer State" column cell may be blank.  I will automatically be alerted of this and this will be corrected
typically within a day or two. This is because the dealer state information is currently maintained in a separate
database and changes only infrequently, so is not dynamically extracted from the website when the inventory is gotten
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

