# yotagrabber

Forked version of major/yotagrabber (major/yotagrabber gets inventory data from Toyota's GraphQL endpoints and
periodically updates and posts csv data files on all the toyota models with that inventory data)

Contains updates due to Toyota website changes and graphql field changes.  Also contains new features/enhancements.

The previously existing vehicles.py was updated to:

- fix Toyota website changes and graphql field changes
 
- fix an issue where it was not getting all the inventory for a given model,
to make it more robust with retries and communication errors, 
and to optionally allow searching for all vehicles within a specified distance from a specified zip code for a given model.
When searching with a specified zipcode you are limited to finding at most 10,000 vehicles for a given model
where as with no specified zipcode you can find at least 40,000 vehicles for a given model.

- Added other spreadsheet columns ( internal Color, cab, bed, transmission type, engine name, , city/highway/combined mpg , 
Dealer city, zipcode, Dealer and Center latitude and longitude, Distance from Center, first date the VIN was added, 
date the row was upgdated from the inventory website)

- Added automatically creating files that contain the Sold inventory for a given model year (i.e.
inventory that no longer appears in the inventory gotten from the website)
These files are <model>_<year>_Sold.csv and <model>_<year>_Sold_raw.parquet files 


Also added a dealers.py program that can generate the dealers.csv file that is used to lookup the dealer Id to
dealer state that vehicles.py uses.

Additionally, added higher level search program searchForVehicles.py that can notify the user via any combination of sound, email, text
whenever changes in the inventory data occur for a specified match criteria.  This allows a user to be alerted whenever what
they are looking, i.e. the result of applying match criteria, has changed (new vins, modified fields, deleted vins)and then look at the attached log file to view 
the changes.  That program uses a config YAML file that can specify how often to search, the match filter criteria filename, 
sound file options, texting options, email options, how changes are reported, log file options, etc.
See SearchVehicles-Example_config.yaml for all the configuration items that can be set

searchForVehicles.py runs the vehicles.py update_vehicles() method to collect an inventory of all vehicles in the US for a desired model
, or all vehicles within a specified distance from a specified zip code for that model, and then runs a specified match criteria against 
that looking for specific vehicles.  Whenever any inventory changes occur for
that match criteria the program notifies the user via any user specified combination of sound, email, text.


I do not currently run the github workflow to update and post the model inventory csv data files to Git at this time.
I have been trying to get that github workflow to run for this but it seems like the main problem is that
Github is having problems communicating with the toyota website by either being blocked sometimes, or getting connection failures/forced closures, or continuous response timeouts.
Possibly the website has been in the past seeing too much traffic from github and is throttling it or blocking it sometimes.
I don't have these problems when running these updates manually on my desktop. 
Because of that, I created a power shell script, Get-ToyotaInventory.ps1, that runs from the desktop, and when scheduled as a job 
does the same thing as the Github workflow, with the exception it uploads the inventory files to a google drive and not Git.
I decided that instead of adding the inventory files to Git, they would be added to a google drive
so as to not worry about any history storage limitations on Git.
There is an optional command line argument to the power shell script that indicates if you want to upload the
inventory files to the google drive (default is not to upload). Note that in order to use that feature
you must use google developers to create a project to enable your google drive to be accessed via that, and must create credentials to be used
for that access.  This is the same as what must be done if you use gmail as the sender source for the email option when running searchForVehicles.py 

See Invocation.txt as to how to invoke the various programs.

