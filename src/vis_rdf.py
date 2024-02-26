import gravis as gv
import networkx as nx
from itertools import product
from rdflib import URIRef, Graph, Namespace, Literal
from rdflib.term import BNode
import uuid

def colour_scheme(name=None):
    # https://www.heavy.ai/blog/12-color-palettes-for-telling-better-stories-with-your-data 
    # https://blog.datawrapper.de/colors-for-data-vis-style-guides/#colors-for-categories
    if name is None:
        name="metro"

    schemes = {"metro" : ["#ea5545", "#f46a9b", "#ef9b20", "#edbf33", "#ede15b", "#bdcf32", "#87bc45", "#27aeef", "#b33dc6"],
               "dutch" : ["#e60049", "#0bb4ff", "#50e991", "#e6d800", "#9b19f5", "#ffa300", "#dc0ab4", "#b3d4ff", "#00bfa0"],
               "nights" : ["#b30000", "#7c1158", "#4421af", "#1a53ff", "#0d88e6", "#00b7c7", "#5ad45a", "#8be04e", "#ebdc78"],
               "pastels" : ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
     }
    if name.lower() not in schemes.keys():
        name="metro"
    return schemes[name]

def cartesian_product_dict_generator(**kwargs):
    k_names=list(kwargs.keys())
    for d in [{k:v[e] for e,k in enumerate(k_names)} for v in product(*kwargs.values())]:
        yield d

def isLiteral(r):
    return isinstance(r, Literal) 

def get_defined_types_set(g):
    return set([o for s,p,o in g.triples((None, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), None))])

def get_object_properties_set(g):
    return set([p for s,p,o in g.triples((None, None, None)) if not isLiteral(o)])

def get_entities_set(g):
    subjects = set([s for s,p,o in g.triples((None, None, None)) if not isLiteral(s)])
    objects = set([o for s,p,o in g.triples((None, None, None)) if not isLiteral(o)])
    return subjects.union(objects)

def get_entity_tag_d(g, entities):
    entities = set([e for b in [(s,o) for s,p,o in g.triples((None, None, None)) if not isLiteral(s) and not isLiteral(o)] for e in b])
    e_labels = set([(s,o) for s,p,o in g.triples((None, URIRef('http://www.w3.org/2000/01/rdf-schema#label'), None)) if not isLiteral(s) and isLiteral(o)])
    e_types = set([(s,o) for s,p,o in g.triples((None, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), None)) if not isLiteral(s) and not isLiteral(o)])
    tagged_d = dict()
    for e in entities:
        for e_k, t in e_types:
            if e_k==e:
                if e not in tagged_d:
                    tagged_d[e]=dict({"label":[], "type":[]})
                tagged_d[e]["type"].append(t)

        for e_k, l in e_labels:
            if e_k==e:
                if e not in tagged_d:
                    tagged_d[e]=dict({"label":[], "type":[]})
                tagged_d[e]["label"].append(l)
        
    return tagged_d

def get_literal_properties_set(g):
    return set([p for s,p,o in g.triples((None, None, None)) if isLiteral(o)])

def resolve_uri_label(label, resolvers=None):
    if isinstance(label, (URIRef,Literal)):
        label=label.toPython()
    if resolvers is None:
        resolvers={}
    for k,v in resolvers.items():
        if v in label:
            return label.replace(v,k+":")
    return label

def get_literals_to_table(graph, entity):
    lit_kvs = [(t[1][t[1].find("#")+1:], t[2].toPython()) for t in graph.triples((entity, None, None)) if isinstance(t[2], Literal)]
    type_kv = [(t[1][t[1].find("#")+1:], t[2].toPython()) for t in graph.triples((entity, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), None)) ]
    for tkv in type_kv:
        lit_kvs.append(tkv)

    table_html_template="""
<table width="95%"><thead><tr><th width="20%">Property</th><th width="80%">Value</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
    """
    
    rows=[]
    row_html_template="""<tr><th>{k}</th><td>{v}</td></tr>"""
    for k,v in lit_kvs:
        
        rows.append(row_html_template.format(k=k,v=v))
    rows = "".join(rows)
    return table_html_template.format(rows=rows)

def get_zeroth(maybe_empty_list):
    if len(maybe_empty_list)==0:
        return None
    else:
        return maybe_empty_list[0]

def process_graph(extended_g):

    resolvers = { "dcterms" : "http://purl.org/dc/terms/", 
            "dc" : "http://purl.org/dc/elements/1.1/",
            "disco":"http://www.tkltd.org/ontologies/discourse#", 
            "serial":"http://www.tkltd.org/ontologies/serialization#",
            "dm" : "http://www.tkltd.org/ontologies/datamodel#",
            "rdfs" : "http://www.w3.org/2000/01/rdf-schema#",
            "rdf" : "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "xsd" : "http://www.w3.org/2001/XMLSchema#", 
            "skos" : "http://www.w3.org/2004/02/skos/core#",
            
            }

    nx_g = nx.MultiDiGraph()
    ents = set()
    language="en"

    type_set = get_defined_types_set(extended_g)
    property_set = get_object_properties_set(extended_g)
    node_styles_g = cartesian_product_dict_generator(
        shape=["circle", "hexagon", "rectangle"],
        color = colour_scheme("metro")
    )
    property_styles_g = cartesian_product_dict_generator(
        color = colour_scheme("metro")
    )
    
    type_styles=dict()
    for t in type_set:
        #skip a style to spread difference
        next(node_styles_g)
        type_styles[t]=next(node_styles_g)

    property_styles=dict()
    for p in property_set:
        property_styles[p]=next(property_styles_g)

    entities = get_entities_set(extended_g)
    tagged_entities = get_entity_tag_d(extended_g, entities)
    label_contents = {k:v.get("label",[str(k)]) for k,v in tagged_entities.items()}
    entity_labels = {k:resolve_uri_label(v,resolvers) for k,v in label_contents.items()}

    entity_types = {k:v.get("type",[None])[0] for k,v in tagged_entities.items()}
    for n in entities:
        label=entity_labels.get(n, n.toPython())
        t=entity_types.get(n, None)
        metadata = """<div align="left">""" + get_literals_to_table(extended_g, n)+ """</div>"""
        nx_g.add_node(n, label=label, **type_styles.get(t, {"color" : "grey", "shape" : "circle"}), click=metadata)
    
    for s,p,o in extended_g.triples((None, None, None)):
        if s in entities and o in entities:
            label=p.toPython()[p.toPython().find("#"):]
            if p != URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
                nx_g.add_edge(s,o, **property_styles.get(t,{"color" : "grey"}), label=label)

    return gv.convert.networkx_to_gjgf(nx_g)

