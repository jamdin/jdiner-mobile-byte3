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
_DB_NAME = 'mobile_data_db' # or whatever name you choose
_USER = 'root'

if (os.getenv('SERVER_SOFTWARE') and
    os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    _DB = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db=_DB_NAME, user=_USER, charset='utf8')
else:
    _DB = MySQLdb.connect(host='173.194.232.250', port=3306, db=_DB_NAME, user=_USER, password = '1234', charset='utf8')


@app.route('/')
def index():
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')

    cursor = _DB.cursor()
    cursor.execute('SHOW TABLES')
    
    logging.info(cursor.fetchall())

    return template.render()

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
