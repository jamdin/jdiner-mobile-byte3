# Imports
import os
import jinja2
import webapp2
import logging
import json
import urllib
import MySQLdb
import math
import numpy as np
from datetime import timedelta, datetime
#import pandas as pd


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# Import the Flask Framework
from flask import Flask, request
app = Flask(__name__)

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

if (os.getenv('SERVER_SOFTWARE') and
    os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    _DB = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db=_DB_NAME, user=_USER, passwd = _PSWD, charset='utf8')
else:
    _DB = MySQLdb.connect(host=_IPADDRESS, port=3306, db=_DB_NAME, user=_USER, passwd = _PSWD, charset='utf8')

cursor = _DB.cursor()


# # turns a unix timestamp into Year-month-day format
# day = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')"
# # turns a unix timestamp into Hour:minute format
# time_of_day = "FROM_UNIXTIME(timestamp/1000,'%H:%i')"
# # calculates the difference between two timestamps in seconds
# elapsed_seconds = "(max(timestamp)-min(timestamp))/1000"
# # the name of the table our query should run on
# table = _ACTIVITY
# # turns a unix timestamp into Year-month-day Hour:minute format
# day_and_time_of_day = "FROM_UNIXTIME(timestamp/100, '%Y-%m-%d %H:%i')"
# # Groups the rows of a table by day and activity (so there will be one 
# # group of rows for each activity that occurred each day.  
# # For each group of rows, the day, time of day, activity name, and 
# # elapsed seconds (difference between maximum and minimum) is calculated, 
# query = "SELECT {0} AS day, {1} AS time_of_day, activity_name, {2} AS time_elapsed_seconds FROM {3} WHERE device_id='{4}'  GROUP BY day, activity_name, {5}".format(day, time_of_day, elapsed_seconds, table, _ID, day_and_time_of_day)

#####################################################################################################
#############                               FUNCTIONS                                   #############
#####################################################################################################


# Takes the database link and the query as input
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

def unique_address(locations_visit, epsilon):#Works with _EPSILON = 0.0001
    addresses = {}
    for location in locations_visit:
        bin = find_bin(bins, location[0], location[1], epsilon)
        if bin not in addresses:
            print(bin, location[4])
            addresses[bin] = location[4]
    return addresses

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

def handle_outliers(list, col_index):
    l_array = np.array(list)
    if l_array.ndim ==1:
        col = l_array
    else:
        col = l_array[:,col_index]
    mean, std, median = col.mean(), col.std(), np.median(col)
    outliers = np.absolute(col - mean) > 2*std
    col[outliers] = median  #Replace outliers with the median
    if l_array.ndim>1:
        l_array[:,col_index] = col
    return l_array

def nearest_temperature(trip, temperatures):
    date = trip[0]
    temp_time = [t[0] for t in temperatures]
    temp_temp = [t[1] for t in temperatures]
    closest_time = min(temp_time, key=lambda d: abs(d - date))
    temp_index = temp_time.index(closest_time)
    if abs(date-closest_time) > timedelta(hours=2):#If the time for the temperature is more than 2 hours away
        temp_range = range(temp_index-2, temp_index+3)
        temp = np.mean([temp_temp[i] for i in temp_range]) #Mean of a window of 5
    else:
        temp = temp_temp[temp_index]
    return temp

def time_to_class(trip, class_start_time):
    date = trip[0]
    weekday = date.strftime('%A')
    #start_time = class_start_time[weekday]
    start_time = datetime.strptime(class_start_time[weekday], '%H:%M').time()
    trip_time = date.time()
    
    class_seconds = (start_time.hour*60*60 + start_time.minute*60 + start_time.second)
    trip_seconds = (trip_time.hour*60*60 + trip_time.minute*60 + trip_time.second)
    delta_minutes = (class_seconds - trip_seconds)/60
    return delta_minutes

def add_missing_hours(aggregated_data):
    complete_array = []
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    hours = range(24)
    day_hour = {}
    keys = []
    for d in days:
        for h in hours:
            day_hour[(d,h)]=0
            keys.append((d,h))

    for a in aggregated_data:
        index = (a[0],a[1])
        count = a[2]
        day_hour[index] = count
    for k in keys:
        value = day_hour[k]
        row = (k[0],k[1],value)
        complete_array.append(row)

    return np.array(complete_array)

#####################################################################################################
#############                           END    FUNCTIONS                                #############
#####################################################################################################

local_time_departure = "CONVERT_TZ(FROM_UNIXTIME(double_departure/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00')"
local_time_arrival = "CONVERT_TZ(FROM_UNIXTIME(double_arrival/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00')"
day_of_week = "DAYNAME(CONVERT_TZ(FROM_UNIXTIME(double_departure/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00'))"
start_date = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')>'2017-01-30'" #Date I returned from NY
#max_time = "TIME(CONVERT_TZ(FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00'))<MAKETIME(16,0,0)"

query = "SELECT double_latitude, double_longitude, {0} AS departure, {1} AS arrival, address, {2} FROM locations_visit WHERE {3};".format(local_time_departure, local_time_arrival, day_of_week, start_date)

locations_visit = make_query(cursor,query)
bins = bin_locations(locations_visit, _EPSILON)

addresses = unique_address(locations_visit, _EPSILON)

norm_locations = normalize_address(locations_visit, addresses, _EPSILON)

trips = join_trips(norm_locations)

start_address_index = 4
end_address_index = 5
total_time_index = 3
start_time_index = 1


commute_toUniv = [t for t in trips if (t[start_address_index] == _HOME) & (t[end_address_index] == _UNIVERSITY) & (t[start_time_index].time() < t[start_time_index].time().replace(hour=16, minute = 0))]
# commute_toUniv = [t for t in trips if (t[start_address_index] == _HOME) & (t[end_address_index] == _UNIVERSITY)]
commute_toHome = [t for t in trips if (t[start_address_index] == _UNIVERSITY) & (t[end_address_index] == _HOME)]

commute_toUniv = handle_outliers(commute_toUniv, total_time_index)
commute_toHome = handle_outliers(commute_toHome, total_time_index)

plot_toUniv = commute_toUniv[:,[start_time_index, total_time_index]]
plot_toUniv[:,1] = plot_toUniv[:,1]/60 #Display in minutes

plot_toHome = commute_toHome[:,[start_time_index, total_time_index]]
plot_toHome[:,1] = plot_toHome[:,1]/60 #Display in minutes


date = "CONVERT_TZ(FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d %H:%i:%s'),'+00:00','-05:00')"
temp_fahr = "1.8*(temperature)-459.67"

query = "SELECT {0} AS Date, {1} AS temperature FROM plugin_openweather WHERE {0}>'2017-01-30'".format(date, temp_fahr);
temp = make_query(cursor, query)

temp_index = 1
temperatures = handle_outliers(temp, temp_index)

closest_temperatures = [nearest_temperature(trip,temperatures) for trip in plot_toUniv]
data_toUniv = np.column_stack((plot_toUniv, closest_temperatures))
data_toUniv = data_toUniv[data_toUniv[:,1].argsort()] #Sort the data
logging.info(data_toUniv)

queries = [{'query':query, 'results':data_toUniv}]


class_start_time = {'Monday': '13:30', 'Tuesday': '09:00', 'Wednesday': '13:30', 'Thursday': '09:00', 'Friday': '15:00'}
time_class = [time_to_class(trip,class_start_time) for trip in plot_toUniv]
time_class = handle_outliers(time_class, 0)
time_toUniv = np.column_stack((plot_toUniv, time_class))
time_toUniv = time_toUniv[time_toUniv[:,1].argsort()]

queries = queries + [{'query':query, 'results':time_toUniv}]

###Aggregate Data

#Walking
day_of_week = "DAYNAME(CONVERT_TZ(FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00'))"
hour_of_day = "HOUR(CONVERT_TZ(FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d %H:%i:%s'), '+00:00','-05:00'))"
activity_name = "'walking'"
order_by_weekday = "FIELD(Weekday, 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY')"
query = "SELECT {0} AS Weekday, {1} AS Hour, COUNT(*) FROM {2} WHERE activity_name = {3} GROUP BY {0},{1} ORDER BY {4}, Hour;".format(day_of_week, hour_of_day, _ACTIVITY, activity_name, order_by_weekday)
walking_aggregated_missing = make_query(cursor,query)

queries_missing = [{'query':query, 'results':walking_aggregated_missing}]
walking_aggregated = add_missing_hours(walking_aggregated_missing)

queries = queries + [{'query':query, 'results':walking_aggregated}]

#Still
activity_name = "'still'"
query = "SELECT {0} AS Weekday, {1} AS Hour, COUNT(*) FROM {2} WHERE activity_name = {3} GROUP BY {0},{1} ORDER BY {4}, Hour;".format(day_of_week, hour_of_day, _ACTIVITY, activity_name, order_by_weekday)
still_aggregated_missing = make_query(cursor,query)
queries_missing = queries_missing + [{'query':query, 'results':still_aggregated_missing}]

still_aggregated = add_missing_hours(still_aggregated_missing)

queries = queries + [{'query':query, 'results':still_aggregated}]

#Running
activity_name = "'running'"
query = "SELECT {0} AS Weekday, {1} AS Hour, COUNT(*) FROM {2} WHERE activity_name = {3} GROUP BY {0},{1} ORDER BY {4}, Hour;".format(day_of_week, hour_of_day, _ACTIVITY, activity_name, order_by_weekday)
running_aggregated_missing = make_query(cursor,query)
queries_missing = queries_missing + [{'query':query, 'results':running_aggregated_missing}]
running_aggregated = add_missing_hours(running_aggregated_missing)

queries = queries + [{'query':query, 'results':running_aggregated}]

#Vehicle
activity_name = "'in_vehicle'"
query = "SELECT {0} AS Weekday, {1} AS Hour, COUNT(*) FROM {2} WHERE activity_name = {3} GROUP BY {0},{1} ORDER BY {4}, Hour;".format(day_of_week, hour_of_day, _ACTIVITY, activity_name, order_by_weekday)
vehicle_aggregated_missing = make_query(cursor,query)
queries_missing = queries_missing + [{'query':query, 'results':vehicle_aggregated_missing}]
vehicle_aggregated = add_missing_hours(vehicle_aggregated_missing)

queries = queries + [{'query':query, 'results':vehicle_aggregated}]




@app.route('/')
def index():
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')

    
    
    context = {'queries':queries}
    return template.render(context)

# @app.route('/_update_table', methods=['POST']) 
# def update_table():
#     logging.info(request.get_json())
#     cols = request.json['cols']
#     logging.info(cols)
#     result = get_all_data(make_query(cols, 10))
#     logging.info(result)
#     return json.dumps({'content' : result['rows'], 'headers' : result['columns']})

@app.route('/about')
def about():
    template = JINJA_ENVIRONMENT.get_template('templates/about.html')
    return template.render()

@app.route('/quality')
def quality():
    template = JINJA_ENVIRONMENT.get_template('templates/quality.html')
    context = {'queries':queries_missing}
    return template.render(context)

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404

@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
    
