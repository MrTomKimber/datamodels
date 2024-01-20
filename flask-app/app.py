# Import flask module
from flask import Flask, request
import jinja2
import pandas as pd


import os, sys
MODPATH=os.path.split(__file__)[0]
sys.path.append(os.path.join(MODPATH,"..","src"))

import repository

file_loader = jinja2.FileSystemLoader("templates/")
static_folder = jinja2.FileSystemLoader("static/")
env = jinja2.Environment(loader=file_loader)
template = env.get_template('html_example.jinja2')

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


STORETYPE = 'jena'
QUERYENDPOINT="http://fuseki:3030/modelg/query"
UPDATEENDPOINT="http://fuseki:3030/modelg/update"
repo = repository.Repository(store_type=STORETYPE,query_url=QUERYENDPOINT, update_url=UPDATEENDPOINT)


@app.route('/')
def index():
    qr=repo.run_cached_query("get_discourse_details.sparql")

    content_str = pd.DataFrame(qr).to_html() + "<br>" + 'Hello to Flask!'
    output_str=template.render(language_code="en", title="Time Teller", appname="timeteller", content= content_str)
    return output_str
 
# main driver function
if __name__ == "__main__":
    app.run()