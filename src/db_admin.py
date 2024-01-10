
from datetime import datetime
from rdflib import URIRef, Literal, Graph, Dataset
import xml.etree.ElementTree as ET
from os import walk
from os.path import isfile, join, abspath
import pathlib
import re

from rdflib.plugins.stores import sparqlstore

def dataset_handle(query_url, update_url):
    jena = sparqlstore.SPARQLUpdateStore(query_url, context_aware=True)
    jena.open((query_url, update_url))
    ds = Dataset(store=jena, default_union=True)
    return ds


def create_named_graph_manifest_rdf_xml(graph_uri, namespaces, properties):
    X = ET.Element('rdf:RDF')
    for prefix, uri  in namespaces:
        X.set("xmlns:" + prefix, uri)
    q = ET.SubElement(X, "rdf:Description")
    q.set("rdf:about", graph_uri)
    for t,v in properties.items():
        a = ET.SubElement(q, t)
        a.text = v
    ET.indent(X, space="\t", level=0)
    return ET.tostring(X).decode()

def read_sparql_repo(sparql_dir, prepend=None):
    ## Pulls out files with a `.sparql` extension from a nested directory
    ## structure rooted at `sparql_dir`
    paths=[]
    queries={}

    for root, dirs, files in walk(sparql_dir):
        for f in files:
            fname = abspath(join(root, f))
            print(pathlib.Path( fname).suffix)
            if pathlib.Path( fname).suffix.lower()==".sparql":
                paths.append(fname)
                
    return paths

def read_sparql_manifest(fname):
    ## Reads a .sparql file, and extracts :parameters: from the markup and returns 
    ## a dictionary of key/value pairs.
    ## A .sparql manifest should include the following parameters in :parm: notation
    ## as part of the inital comment block. 
    ##
    ## path:
    ## title:
    ## description
    ## parameters
    ## returns
    ## query
    
    manifest={"path":fname}
    with open(fname, "r") as f:
        text = f.read()
    
    parser_rgx=re.compile("#?\s\:(\w*)\:?\s(.*)")
    groups = parser_rgx.findall(text)
    for g in groups:
        manifest[g[0]]=g[1]

    return manifest

    

        

