import gravis as gv
import networkx as nx
from rdflib import URIRef, Graph, Namespace, Literal
from rdflib.term import BNode

def isURIRef(r):
    return isinstance(r, URIRef)

def isBNode(r):
    return isinstance(r, BNode)

def get_concrete_owl_classes(owl_graph):
    return filter(isURIRef, (s for s,p,o in owl_graph.triples((None, None, URIRef('http://www.w3.org/2002/07/owl#Class')))))

def get_concrete_owl_object_properties(owl_graph):
    return filter(isURIRef, (s for s,p,o in owl_graph.triples((None, None, URIRef('http://www.w3.org/2002/07/owl#ObjectProperty')))))

def get_concrete_owl_data_properties(owl_graph):
    return filter(isURIRef, (s for s,p,o in owl_graph.triples((None, None, URIRef('http://www.w3.org/2002/07/owl#DatatypeProperty')))))

def get_class_subclass_relations(owl_graph):
    return ((s,o) for s,p,o in owl_graph.triples((None, URIRef('http://www.w3.org/2000/01/rdf-schema#subClassOf'),  None)))

def process_bnode(owl_graph, bnode):
    #print(bnode)
    #print(list(owl_graph.triples((bnode, None, None))))
    # Look for contents that might be expressed using union/intersection or complement
    i_u_c = set([URIRef('http://www.w3.org/2002/07/owl#unionOf'), 
                URIRef('http://www.w3.org/2002/07/owl#intersectionOf'), 
                URIRef('http://www.w3.org/2002/07/owl#complementOf'), 
                URIRef('http://www.w3.org/2002/07/owl#oneOf')])
    if any((p in i_u_c for s,p,o in owl_graph.triples((bnode, None, None)))):
        u_pointers = set((o for s,p,o in owl_graph.triples((bnode, URIRef('http://www.w3.org/2002/07/owl#unionOf'), None))))
        i_pointers = set((o for s,p,o in owl_graph.triples((bnode, URIRef('http://www.w3.org/2002/07/owl#intersectionOf'), None))))
        o_pointers = set((o for s,p,o in owl_graph.triples((bnode, URIRef('http://www.w3.org/2002/07/owl#oneOf'), None))))
        if len (u_pointers)>0:
            union_nodes = get_rdf_collection(owl_graph, u_pointers.pop())
            return union_nodes
        elif len (i_pointers)>0:
            intersection_nodes=get_rdf_collection(owl_graph, i_pointers.pop())
            return intersection_nodes
        elif len (o_pointers)>0:
            oneof_nodes=get_rdf_collection(owl_graph, o_pointers.pop())
            return oneof_nodes
        

    
def get_node_label(owl_graph, node, resolvers=None):
    labels = set([o for s,p,o in owl_graph.triples((node, URIRef('http://www.w3.org/2000/01/rdf-schema#label'),None))])
    if len(labels)>0:
        return labels.pop().toPython()
    else:
        if resolvers is not None:
            return resolve_uri_label(node.toPython(), resolvers)
        return node.toPython()

def get_node_literals(owl_graph, node, resolvers=None):
    literals = set([(p,o) for s,p,o in owl_graph.triples((node, None,None)) if isinstance(o,Literal)])
    if len(literals)>0:
        return {resolve_uri_label(k, resolvers) : str(v) for k,v in literals}
    

def dict_to_html_table(kv_dict):
    if kv_dict is None:
        kv_dict={}
    rows = ""
    for k,v in kv_dict.items():
        rows = rows + f"""<tr><td>{k}</td><td>{v}</td></tr>"""
    table = f"""<table width="95%"><tr>
    <th width="20%">Key</th><th width="80%">Value</th>
    </tr>
    {rows}
    </table>"""
    return table
    
def resolve_uri_label(label, resolvers=None):
    if isinstance(label, (URIRef,Literal)):
        label=label.toPython()
    if resolvers is None:
        resolvers={}
    for k,v in resolvers.items():
        if v in label:
            return label.replace(v,k+":")
        
    return label

def get_rdf_collection(owl_graph, collection_pointer, collection=None):
    #print(collection_pointer)
    if collection is None:
        collection=set()
    try:
        first = set((o for s,p,o in owl_graph.triples((collection_pointer, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#first'), None)))).pop()
    except KeyError:
    
        return collection
    collection.add(first)
    try:
        rest = set((o for s,p,o in owl_graph.triples((collection_pointer, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#rest'), None)))).pop()
    except KeyError:
    
        return collection
    
    if rest == URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#nil'):
    
        return collection
    else:
    
        get_rdf_collection(owl_graph, rest, collection=collection)
    
    return collection

def get_orientable_owl_object_properties(owl_graph, p_list):
    d_classes = []
    for p in p_list:
        d_set = set((d for pr,x,d in owl_graph.triples((p, URIRef('http://www.w3.org/2000/01/rdf-schema#domain'), None))))

        r_set = set((r for pr,x,r in owl_graph.triples((p, URIRef('http://www.w3.org/2000/01/rdf-schema#range'), None))))

        if any((isBNode(d) for d in d_set)):
            dx_set = set()
            for d in d_set:
                if isBNode(d):
                    dx_set.update(process_bnode(owl_graph,d ))
            #dx_set = [process_bnode(owl_graph, d) for d in d_set if isBNode(d)]
        else:
            dx_set = d_set
        if any((isBNode(r) for r in r_set)):
            #print("!", r_set)
            rx_set = set()
            for r in r_set:
                if isBNode(r):
                    #print("!B!", r, rx_set, process_bnode(owl_graph, r))
                    rx_set.update(process_bnode(owl_graph, r))
                    
                    if all([isinstance(r, Literal) for r in rx_set]):
                        rx_set=set([Literal(str({r.toPython() for r in rx_set}))])
        else:
            rx_set = r_set
        

        for d in dx_set:
            for r in rx_set:
                d_classes.append(tuple((p,d,r)))
    return d_classes

def gen_gjgf_from_owl_model_graph(owl_graph):
    lst_dplist = list(get_orientable_owl_object_properties(owl_graph, get_concrete_owl_data_properties(owl_graph)))
    dptypes = dict()
    nodes=dict()
    processed_lst_dplist=[]
    for l,s,t in lst_dplist:
        if isinstance(t, URIRef):
            if t not in dptypes:
                dptypes[t]=1
            else:
                dptypes[t]=dptypes[t]+1
            node_key = f"{str(t.toPython())}_{dptypes[t]}"
            nodes[node_key]=(t,"hexagon", "green")
        else:
            node_key=t.toPython()
            nodes[node_key]=(t.toPython(),"rectangle", "red")
        processed_lst_dplist.append((l,s,node_key))


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

    for n in list(get_concrete_owl_classes(owl_graph)):
        nx_g.add_node(n, label=get_node_label(owl_graph,n,resolvers), shape="circle", click=dict_to_html_table(get_node_literals(owl_graph, n, resolvers)))
        
    for k,v in nodes.items():
        nx_g.add_node(k, label=resolve_uri_label(v[0], resolvers), shape=v[1], color=v[2], click=dict_to_html_table(get_node_literals(owl_graph, k, resolvers)))

    for s,t in list(get_class_subclass_relations(owl_graph)):
        nx_g.add_edge(s,t,label="owl:subClassOf", color="grey")
        
    for l,s,t in list(get_orientable_owl_object_properties(owl_graph, get_concrete_owl_object_properties(owl_graph))):
        nx_g.add_edge(s,t,label=get_node_label(owl_graph,l,resolvers),color="blue")

    for l,s,t in processed_lst_dplist:
        nx_g.add_edge(s,t,label=get_node_label(owl_graph,l,resolvers),color="red")

    return gv.convert.networkx_to_gjgf(nx_g)

