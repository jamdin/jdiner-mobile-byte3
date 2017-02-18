import MySQLdb
import math
import numpy as np
import logging
# from geopy.geocoders import Nominatim

_INSTANCE_NAME = 'jdiner-mobile-byte3:mobile-data'
_DB_NAME = 'mobile_data_db'
_USER = 'root'
_IPADDRESS = '173.194.232.250'
_PSWD = '1234'
_ACTIVITY = 'plugin_google_activity_recognition'
_LOCATIONS = 'locations'
_ID = 'ab755be6-a980-4d95-a229-6d2af7c35bbf'
_EPSILON = 0.0001
_HOME = '5440 5th Ave, Pittsburgh, PA  15232, United States'
_UNIVERSITY = 'Carnegie Mellon University, 4902 Forbes Ave, Pittsburgh, PA  15213, United States'

_DB = MySQLdb.connect(host=_IPADDRESS, port=3306, db=_DB_NAME, user=_USER, passwd = _PSWD, charset='utf8')
cursor = _DB.cursor()
print("connected")
# geolocator = Nominatim()

def make_query(cursor, query):
    # this is for debugging -- comment it out for speed
    # once everything is working

    try:
        # try to run the query
        cursor.execute(query)
        # and return the results
        return cursor.fetchall()
    
    except Exception:
        # if the query failed, log that fact
        logging.info("query making failed")
        logging.info(query)

        # finally, return an empty list of rows 
        return []

# helper function to make a query and print lots of 
# information about it. 
def make_and_print_query(cursor, query, description):
    logging.info(description)
    logging.info(query)
    
    rows = make_query(cursor, query)
        
def bin_locations(locations, epsilon):
    # always add the first location to the bin
    bins = {1: [locations[0][0], locations[0][1]]}
    # this gives us the current maximum key used in our dictionary
    num_places = 1
    
    # now loop through all the locations 
    for location in locations:
        lat = location[0]
        lon = location[1]
        # assume that our current location is new for now (hasn't been found yet)
        place_found = False
        # loop through the bins 
        for place in bins.values():
            # check whether the distance is smaller than epsilon
            if distance_on_unit_sphere(lat, lon, place[0], place[1]) < epsilon:
                #(lat, lon) is near  (place[0], place[1]), so we can stop looping
                place_found = True
                    
        # we weren't near any of the places already in bins
        if place_found is False:
            logging.info("new place: {0}, {1}".format(lat, lon))
            # increment the number of places found and create a new entry in the 
            # dictionary for this place. Store the lat lon for comparison in the 
            # next round of the loop
            num_places = num_places + 1
            bins[num_places] = [lat, lon]

    return bins.values()
            
def find_bin(bins, lat, lon, epsilon):
    for i in range(len(bins)):
        blat = bins[i][0]
        blon = bins[i][1]
        if distance_on_unit_sphere(lat, lon, blat, blon) < epsilon:
            return i
    bins.append([lat, lon])
    return len(bins)-1

def group_activities_by_location(bins, locations, activities, epsilon):
    searchable_locations = {}
    for location in locations:
        # day, hour
        key = (location[0], location[1])
        if key in searchable_locations:
            # lat,   lon 
            searchable_locations[key] = locations[key] + [(location[2], location[3])]
        else:
            searchable_locations[key] = [(location[2], location[3])]
    
    # a place to store activities for which we couldn't find a location
    # (indicates an error in either our data or algorithm)
    no_loc = []
    for activity in activities:
        # collect the information we will need 
        aday = activity[0] # day
        ahour = activity[1] # hour
        aname = activity[2] # name
        logging.info(aday + aname)
        try: 
            possible_locations = searchable_locations[(aday, ahour)]
            # loop through the locations
            for location in possible_locations:
                logging.info(" about to find bin")
                bin = find_bin(bins, location[0], location[1], epsilon)
                # and add the information to it
                bins[bin] = bins[bin] + [aname]
        except KeyError:
            no_loc.append([aname])

    # add no_loc to the bins
    bins.append(no_loc)
    # this function is taken verbatim from http://www.johndcook.com/python_longitude_latitude.html

def distance_on_unit_sphere(lat1, long1, lat2, long2):

    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
    
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
    
    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
    
    # Compute spherical distance from spherical coordinates.
    
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
        
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
           math.cos(phi1)*math.cos(phi2))
    # sometimes small errors add up, and acos will fail if cos > 1
    if cos>1: cos = 1
    arc = math.acos( cos )
    
    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc


query = "SELECT double_latitude, double_longitude, FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d %H:%i') FROM {0} WHERE device_id = '{1}' AND FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')>'2017-01-30' AND (FROM_UNIXTIME(timestamp/1000,'%H:%i')>'08:30' AND FROM_UNIXTIME(timestamp/1000,'%H:%i')<'15:30')".format(_LOCATIONS, _ID)
locations = make_query(cursor, query)
print("Termino primer query")

query = "SELECT double_latitude, double_longitude, COUNT(*) AS count FROM locations WHERE FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')>'2017-01-29' GROUP BY double_latitude, double_longitude ORDER BY count DESC LIMIT 10;"
locations = make_query(cursor, query)


print("Termino primer query")
bins = bin_locations(locations, _EPSILON)


#Bin Address location_visit
query = "SELECT DISTINCT double_latitude, double_longitude FROM locations_visit;"
locations = make_query(cursor, query)
bins = bin_locations(locations, _EPSILON)
num_bins = len(bins)

local_time_departure = "CONVERT_TZ(FROM_UNIXTIME(double_departure/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00')"
local_time_arrival = "CONVERT_TZ(FROM_UNIXTIME(double_arrival/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00')"
day_of_week = "DAYNAME(CONVERT_TZ(FROM_UNIXTIME(double_departure/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00'))"
start_date = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')>'2017-01-30'" #Date I returned from NY

query = "SELECT double_latitude, double_longitude, {0} AS departure, {1} AS arrival, address, {2} FROM locations_visit WHERE {3};".format(local_time_departure, local_time_arrival, day_of_week, start_date)
print(query)
locations_visit = make_query(cursor,query)

def unique_address(locations_visit, epsilon):#Works with _EPSILON = 0.0001
    addresses = {}
    for location in locations_visit:
        bin = find_bin(bins, location[0], location[1], epsilon)
        if bin not in addresses:
            print(bin, location[4])
            addresses[bin] = location[4]
    return addresses

addresses = unique_address(locations_visit, _EPSILON)


def normalize_address(locations, addresses, epsilon):
    loc_list = []
    for loc in locations:
        #print(loc_list)
        location = list(loc)
        bin = find_bin(bins, location[0], location[1], epsilon)
        normalized_add = addresses.get(bin)
        location[4] = normalized_add
        loc_list.append(location)
    return loc_list

norm_locations = normalize_address(locations_visit, addresses, _EPSILON)


def join_trips(norm_locations):
    i=0
    maxi = len(norm_locations)
    trips = []
    while i<maxi:
        day_of_week = norm_locations[i][5]
        start = norm_locations[i][2]
        if start == None:
            i+=1
            if i<maxi:
                start = norm_locations[i][2]
        if i<maxi:
            start_address = norm_locations[i][4]
        i+=1
        if i<maxi:
            end = norm_locations[i][3]
            end_address = norm_locations[i][4]
            if None not in (start, end):
                total_time = (end - start).total_seconds() #Total seconds of the trip
                trip = [day_of_week, start, end, total_time, start_address, end_address]
                trips.append(trip)
            if norm_locations[i][2] == None: #If departure is None
                i+=1
    return trips

join_trips(norm_locations)

trips = join_trips(norm_locations)

start_address_index = 4
end_address_index = 5
total_time_index = 3
start_time_index = 1

commute_toUniv = [t for t in trips if (t[start_address_index] == _HOME) & (t[end_address_index] == _UNIVERSITY)]
commute_toHome = [t for t in trips if (t[start_address_index] == _UNIVERSITY) & (t[end_address_index] == _HOME)]

for c in commute_toUniv:
    print(c)

for c in commute_toHome:
    print(c)

def handle_outliers(list, col_index):
    l_array = np.array(list)
    col = l_array[:,col_index]
    mean, std, median = col.mean(), col.std(), np.median(col)
    outliers = np.absolute(col - mean) > 2.5*std
    col[outliers] = median  #Replace outliers with the median
    l_array[:,col_index] = col
    return l_array


commute_toUniv = handle_outliers(commute_toUniv, total_time_index)
commute_toHome = handle_outliers(commute_toHome, total_time_index)

plot_toUniv = commute_toUniv[:,[start_time_index, total_time_index]]
plot_toUniv[:,1] = plot_toUniv[:,1]/60 #Display in minutes

plot_toHome = commute_toHome[:,[start_time_index, total_time_index]]
plot_toHome[:,1] = plot_toHome[:,1]/60 #Display in minutes

print(plot_toUniv)
print(plot_toHome)
