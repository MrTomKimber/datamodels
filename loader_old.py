
import pandas as pd
import owlready2 as owlr
#https://pythonhosted.org/Owlready/
import rdflib
from rdflib import URIRef, Literal
from rdflib.namespace import RDF, RDFS
from rdflib import Namespace
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph

from collections import Counter
import uuid

import networkx as nx
