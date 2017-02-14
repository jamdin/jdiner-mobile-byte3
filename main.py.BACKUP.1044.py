# Imports
import os
import jinja2
import webapp2
import logging
import json
import urllib
import MySQLdb


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
_ID = 'ab755be6-a980-4d95-a229-6d2af7c35bbf'

if (os.getenv('SERVER_SOFTWARE') and
    os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    _DB = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db=_DB_NAME, user=_USER, passwd = _PSWD, charset='utf8')
else:
<<<<<<< HEAD
<<<<<<< HEAD
    _DB = MySQLdb.connect(host=_IPADDRESS, port=3306, db=_DB_NAME, user=_USER, passwd = _PSWD, charset='utf8')
=======
    _DB = MySQLdb.connect(host='173.194.232.250', port=3306, db=_DB_NAME, user=_USER, password = '1234', charset='utf8')
>>>>>>> 808dc00069ed95c744b093fd348b30831dc1ea8b
=======
    _DB = MySQLdb.connect(host=_IPADDRESS, port=3306, db=_DB_NAME, user=_USER, passwd = _PSWD, charset='utf8')
>>>>>>> 88512f2e981beec25c89f1f657ae01142d6d90da

# turns a unix timestamp into Year-month-day format
day = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')"
# turns a unix timestamp into Hour:minute format
time_of_day = "FROM_UNIXTIME(timestamp/1000,'%H:%i')"
# calculates the difference between two timestamps in seconds
elapsed_seconds = "(max(timestamp)-min(timestamp))/1000"
# the name of the table our query should run on
table = _ACTIVITY
# turns a unix timestamp into Year-month-day Hour:minute format
day_and_time_of_day = "FROM_UNIXTIME(timestamp/100, '%Y-%m-%d %H:%i')"
# Groups the rows of a table by day and activity (so there will be one 
# group of rows for each activity that occurred each day.  
# For each group of rows, the day, time of day, activity name, and 
# elapsed seconds (difference between maximum and minimum) is calculated, 
query = "SELECT {0} AS day, {1} AS time_of_day, activity_name, {2} AS time_elapsed_seconds FROM {3} WHERE device_id='{4}'  GROUP BY day, activity_name, {5}".format(day, time_of_day, elapsed_seconds, table, _ID, day_and_time_of_day)

@app.route('/')
def index():
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')

    cursor = _DB.cursor()
    cursor.execute('SHOW TABLES')
    
    logging.info(cursor.fetchall())
    
    cursor.execute(query)
    result = cursor.fetchall()
    logging.info(result)
    queries = [{'query':query, 'results':result}]
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

# @app.route('/about')
# def about():
#     template = JINJA_ENVIRONMENT.get_template('templates/about.html')
#     return template.render()

# @app.route('/quality')
# def quality():
#     template = JINJA_ENVIRONMENT.get_template('templates/quality.html')
#     return template.render()

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404

@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
