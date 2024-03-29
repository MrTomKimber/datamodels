import os, sys

MODPATH=os.path.split(__file__)[0]
sys.path.append(os.path.join(MODPATH,"..","src"))

import repository

STORETYPE = 'jena'
QUERYENDPOINT="http://fuseki:3030/modelg/query"
UPDATEENDPOINT="http://fuseki:3030/modelg/update"
UPLOAD_FOLDER="uploads/"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','rdf','owl','xlsx','csv'}

sparql_folder = "ui_sparql/"
repo = repository.Repository(store_type=STORETYPE,query_url=QUERYENDPOINT, update_url=UPDATEENDPOINT)
