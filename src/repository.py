"""A repository provides the storage and access methods required for managing a set of artefacts. 
It can be hosted in memory, or can be serialized through a sparql-store interface. """
from rdflib.plugins.stores import sparqlstore, memory
import rdflib
from rdflib import URIRef, Literal, Graph, Dataset, Namespace
from rdflib.namespace import RDF, RDFS
from models.core.serialization import serialization
from models.core.discourse import discourse
import loader
import os

loc_dir = os.path.dirname(os.path.realpath(__file__))

class Repository(object):
    def __init__(self, store_type="memory", **kwargs):
        if 'query_url' in kwargs:
            QUERYURL=kwargs['query_url']
        else:
            QUERYURL="http://localhost:3030/modelg/query"
        if 'update_url' in kwargs:
            UPDATEURL=kwargs['update_url']
        else:
            UPDATEURL="http://localhost:3030/modelg/update"
        
        if store_type=="memory":
            self.store = memory.Memory()
        elif store_type=="jena":
            self.store = sparqlstore.SPARQLUpdateStore(QUERYURL,context_aware=True)
            self.store.open((QUERYURL, UPDATEURL))
        self.ds = Dataset(store=self.store, default_union=True, default_graph_base="http://base.raw")
        self.registered_serializations_uri = "http://config"
        self.master_graph_uri = "http://master"
        self.discourse_graph_uri = "http://discourse"

        ## Initialise Graphs
        self.serialization_graph = self.ds.graph(URIRef(self.registered_serializations_uri))
        if len(self.serialization_graph)==0:
            self.serialization_graph.parse(os.path.join(loc_dir,"graphs", "serial_graph.rdf"))
        serns = Namespace(serialization.serial.base_iri)
        self.serialization_graph.bind('ser', serns, override=True, replace=True)

        self.master_graph = self.ds.graph(URIRef(self.master_graph_uri))
        if len(self.master_graph)==0:
            self.master_graph.parse(os.path.join(loc_dir,"graphs", "master_graph.rdf"))

        self.discourse_graph = self.ds.graph(URIRef(self.discourse_graph_uri))
        if len(self.discourse_graph)==0:
            self.discourse_graph.parse(os.path.join(loc_dir,"graphs", "discourse_graph.rdf"))
        
        self.update_discourse_hashes()

    def truncate_graph(self, graph_uri):
        self.ds.update("""CLEAR GRAPH <{g}>""".format(g=graph_uri))
        self.ds.update("""CREATE GRAPH <{g}>""".format(g=graph_uri))


    @staticmethod
    def meta_data_package_template(field_d):
        dc_terms_base = "http://purl.org/dc/terms/"
        rdf_form = {}
        for k,v in field_d.items():
            rdf_form[URIRef(dc_terms_base + k)] = Literal(v)
        return rdf_form

    @staticmethod
    def triples_to_quads(triples, graph):
        for s,p,o, *_ in triples:
            yield (s,p,o,URIRef(graph))

    def _get_discourse_hashes(self):
        
        with open(os.path.join(loc_dir,"SPARQL", "get_discourse_details.sparql"),"r") as f:
            discourse_details_sparql = f.read()

        qr = self.ds.query(discourse_details_sparql)
        results = list([{k:v[e] for e,k in enumerate([v.n3()[1:] for v in qr.vars])} for v in qr])
        return [(v['hash'].n3()[1:-1], v['discourse'].n3()[1:-1]) for v in results]
    
    def update_discourse_hashes(self):
        self.discourse_hashes=self._get_discourse_hashes()
    
    def register_serialization(self, serialization_path):
        self.serialization_graph.parse(serialization_path)

    def load_serialization_to_discourse(self, serialization_name, title, metadata_payload, datarows):
        #1) Test Serialization Exists
        #2) Get discourse hashes
        #3) Compute new hash
        #4) Test pre-existence
        #5) Load data
        hashes = [h[0] for h in self.discourse_hashes]

        loader.load_to_graph(self.ds, self.registered_serializations_uri, serialization_name, datarows, self.master_graph_uri, self.discourse_graph_uri, title , metadata_payload, fingerprint_hashes=hashes, override_duplicate=False)
        self.update_discourse_hashes()

    @staticmethod    
    def _un_rdflib(value):
        if isinstance(value, URIRef):
            return value.toPython()
        elif isinstance(value, Literal):
            return value.toPython()
        else:
            return value
        
    @staticmethod
    def _flatten_rdflib_query_results(query_results, native_rdflib=False):
        for row in query_results:
            if native_rdflib:
                yield {query_results.vars[e].toPython()[1:]:v for e,v in enumerate(row)}
            else:
                yield {query_results.vars[e].toPython()[1:]:Repository._un_rdflib(v) for e,v in enumerate(row)}

    def run_cached_query(self, q_name, parameters=None, native_rdflib=None):
        if native_rdflib is None:
            native_rdflib = False
        loc_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(loc_dir,"SPARQL", q_name),"r") as f:
            query_sparql = f.read()
        if isinstance(parameters, (list)) and len (parameters)>0:
            for e,p in enumerate(parameters):
                print(("%%p{e}%%".format(e=e), p))
                query_sparql = query_sparql.replace("%%p{e}%%".format(e=e), p)
        print(query_sparql)
        qr = list(Repository._flatten_rdflib_query_results(self.ds.query(query_sparql),native_rdflib))
        return qr
        
