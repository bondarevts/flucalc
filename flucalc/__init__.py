import logging

import flask

from config import Config

app = flask.Flask(__name__)
app.config.from_object(Config)

logging_level = logging.INFO
logging.basicConfig(filename='flucalc.log', level=logging_level,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')


from . import routes
