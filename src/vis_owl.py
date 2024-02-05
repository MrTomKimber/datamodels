import gravis as gv
import networkx as nx
from rdflib import URIRef, Graph, Namespace, Literal
from rdflib.term import BNode
import uuid

class Anonymous():
    def __init__(self, v):
        self.id=v

def isAnonymous(r):
    return isinstance(r, Anonymous)

def isURIRef(r):
    return isinstance(r, URIRef) and not isBNode(r)

def isLiteral(r):
    return isinstance(r, Literal) 

def isBNode(r):
    return detect_bnode(r,"http://www.tkltd.org/.well-known/skolem")

def get_concrete_owl_classes(owl_graph):
    return filter(isURIRef, (s for s,p,o in owl_graph.triples((None, None, URIRef('http://www.w3.org/2002/07/owl#Class')))))

def get_concrete_owl_object_properties(owl_graph):
    return filter(isURIRef, (s for s,p,o in owl_graph.triples((None, None, URIRef('http://www.w3.org/2002/07/owl#ObjectProperty')))))

def get_concrete_owl_data_properties(owl_graph):
    return filter(isURIRef, (s for s,p,o in owl_graph.triples((None, None, URIRef('http://www.w3.org/2002/07/owl#DatatypeProperty')))))

def get_class_subclass_relations(owl_graph):
    return ((s,o) for s,p,o in owl_graph.triples((None, URIRef('http://www.w3.org/2000/01/rdf-schema#subClassOf'),  None)))

def detect_bnode(candidate, skolem_uri):
    if isinstance(candidate, BNode) or \
        (isinstance(candidate, URIRef) and str(candidate.toPython()).startswith(skolem_uri)):
        return True
    return False

def process_bnode(owl_graph, bnode):
    #print(bnode)
    #print(list(owl_graph.triples((bnode, None, None))))
    # Look for contents that might be expressed using union/intersection or complement
    i_u_c = set([URIRef('http://www.w3.org/2002/07/owl#unionOf'), 
                URIRef('http://www.w3.org/2002/07/owl#intersectionOf'), 
                URIRef('http://www.w3.org/2002/07/owl#complementOf'), 
                URIRef('http://www.w3.org/2002/07/owl#oneOf'),
                URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')])
    if any((p in i_u_c for s,p,o in owl_graph.triples((bnode, None, None)))):
        u_pointers = set((o for s,p,o in owl_graph.triples((bnode, URIRef('http://www.w3.org/2002/07/owl#unionOf'), None))))
        i_pointers = set((o for s,p,o in owl_graph.triples((bnode, URIRef('http://www.w3.org/2002/07/owl#intersectionOf'), None))))
        o_pointers = set((o for s,p,o in owl_graph.triples((bnode, URIRef('http://www.w3.org/2002/07/owl#oneOf'), None))))
        t_values = set((o for s,p,o in owl_graph.triples((bnode, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), None)))) #URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
        if len (u_pointers)>0:
            union_nodes = get_rdf_collection(owl_graph, u_pointers.pop())
            return union_nodes
        elif len (i_pointers)>0:
            intersection_nodes=get_rdf_collection(owl_graph, i_pointers.pop())
            return intersection_nodes
        elif len (o_pointers)>0:
            oneof_nodes=get_rdf_collection(owl_graph, o_pointers.pop())
            return oneof_nodes
        elif len (t_values)>0:
            t_nodes=t_values
            return t_nodes
        

    raise Exception(str(list(((p,o) for s,p,o in owl_graph.triples((bnode, None, None))))))
    

    
def get_node_label(owl_graph, node, resolvers=None, language=None):
    if language is None:
        labels = set([o for s,p,o in owl_graph.triples((node, URIRef('http://www.w3.org/2000/01/rdf-schema#label'),None))])
    else:
        labels = set([o for s,p,o in owl_graph.triples((node, URIRef('http://www.w3.org/2000/01/rdf-schema#label'),None)) if o.language is None or o.language==language])
    if len(labels)>0:
        return labels.pop().toPython()
    else:
        if resolvers is not None:
            if isinstance(node,str):
                return resolve_uri_label(node, resolvers)    
            return resolve_uri_label(node.toPython(), resolvers)
        return node.toPython()

def get_node_literals(owl_graph, node, resolvers=None, language=None):
    if language is None:
        literals = set([(p,o) for s,p,o in owl_graph.triples((node, None,None)) if isinstance(o,Literal)])
    else:
        literals = set([(p,o) for s,p,o in owl_graph.triples((node, None,None)) if (isinstance(o,Literal) and o.language is None) or (isinstance(o,Literal) and o.language==language)])
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

def property_hierarchy(owl_graph, property, p_set=None):
    if p_set is None:
        p_set=set()
    p_set.add(property)
    superproperties = owl_graph.triples((property,URIRef('http://www.w3.org/2000/01/rdf-schema#subPropertyOf'),None))
    for s in superproperties:
        p_set=property_hierarchy(owl_graph, s[2], p_set)
    return p_set

def get_orientable_properties(owl_graph, p_list):
    # An "orientable" object property is an object property for which there is a defined domain and range. 
    # In most cases, these domains and ranges will be explicitly defined, but they could be determined by
    # an arbitrarily long chain of subProperty relationships.
    d_classes = []
    for p in p_list:
        # Fill starter d_set will immediately available domain values associated with the property
        ph = property_hierarchy(owl_graph, p)
        d_set = set()
        for px in ph:
            d_set = d_set.union(set((d for pr,x,d in owl_graph.triples((px, URIRef('http://www.w3.org/2000/01/rdf-schema#domain'), None)))))
        r_set = set()
        for px in ph:
            r_set = r_set.union(set((r for pr,x,r in owl_graph.triples((px, URIRef('http://www.w3.org/2000/01/rdf-schema#range'), None)))))

        if any((isBNode(d) for d in d_set)):
            dx_set = set()
            for d in d_set:
                if isBNode(d):
                    dx_set.update(process_bnode(owl_graph,d ))
            #dx_set = [process_bnode(owl_graph, d) for d in d_set if isBNode(d)]
        else:
            dx_set = d_set

        if any((isBNode(r) for r in r_set)):
            print("!", p, r_set)
            rx_set = set()
            for r in r_set:
                if isBNode(r):
                    print("!B!", f"r:{str(r)}, rx_set{str(rx_set)}", process_bnode(owl_graph, r))
                    rx_set.update(process_bnode(owl_graph, r))
                    
            if all([isinstance(r, Literal) for r in rx_set]):
                rx_set=set([Literal(str({r.toPython() for r in rx_set}))])
        else:
            rx_set = r_set
        
        if len(rx_set)==0:
            gid = uuid.uuid4().hex
            rx_set.add(Anonymous(gid))
        
        if len(dx_set)==0:
            gid = uuid.uuid4().hex
            dx_set.add(Anonymous(gid))

        for d in dx_set:
            
                
            for r in rx_set:
                d_classes.append(tuple((p,d,r)))

    return d_classes

def gen_gjgf_from_owl_model_graph(owl_graph):
    lst_dplist = list(get_orientable_properties(owl_graph, get_concrete_owl_data_properties(owl_graph)))
    dptypes = dict()
    nodes=dict()
    processed_lst_dplist=[]
    for l,s,t in lst_dplist:
        if isURIRef(t):
            if t not in dptypes:
                dptypes[t]=1
            else:
                dptypes[t]=dptypes[t]+1
            node_key = f"{str(t.toPython())}_{dptypes[t]}"
            nodes[node_key]=(t,"hexagon", "green")
        elif isLiteral(t):
            node_key=t.toPython()
            nodes[node_key]=(t.toPython(),"rectangle", "red")
        elif isAnonymous(t):
            node_key=t.id
            nodes[node_key]=("","circle", "white")

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
    language="en"
    for n in list(get_concrete_owl_classes(owl_graph)):
        nx_g.add_node(n, label=get_node_label(owl_graph,n,resolvers,language), shape="circle", click=dict_to_html_table(get_node_literals(owl_graph, n, resolvers, language="en")))
        
    for k,v in nodes.items():
        nx_g.add_node(k, label=get_node_label(owl_graph,v[0], resolvers,language), shape=v[1], color=v[2], click=dict_to_html_table(get_node_literals(owl_graph, k, resolvers, language="en")))

    for s,t in list(get_class_subclass_relations(owl_graph)):
        if s not in nx_g.nodes():
            if isBNode(s):
                children=process_bnode(owl_graph,s)
                for c in children:
                    nx_g.add_node(c,label=get_node_label(owl_graph,c, resolvers,language), shape="circle", color="grey", click=dict_to_html_table(get_node_literals(owl_graph, c, resolvers, language="en")))
            elif isAnonymous(s):
                nx_g.add_node(s,label="", shape="circle", color="white", click="")
            else:
                nx_g.add_node(s,label=get_node_label(owl_graph,s, resolvers,language), shape="circle", color="orange", click=dict_to_html_table(get_node_literals(owl_graph, s, resolvers, language="en")))
        if t not in nx_g.nodes():
            if isBNode(t):
                children=process_bnode(owl_graph,t)
                for c in children:
                    nx_g.add_node(c,label=get_node_label(owl_graph,c, resolvers,language), shape="circle", color="grey", click=dict_to_html_table(get_node_literals(owl_graph, c, resolvers, language="en")))
            elif isAnonymous(t):
                nx_g.add_node(t,label="", shape="circle", color="white", click="")

            else:
                nx_g.add_node(t,label=get_node_label(owl_graph,t, resolvers,language), shape="circle", color="orange", click=dict_to_html_table(get_node_literals(owl_graph, t, resolvers, language="en")))



        nx_g.add_edge(s,t,label="owl:subClassOf", color="grey")
        
    for l,s,t in list(get_orientable_properties(owl_graph, get_concrete_owl_object_properties(owl_graph))):
        if s not in nx_g.nodes():
            if isAnonymous(s):
                nx_g.add_node(s,label="", shape="circle", color="white", click="")
            else:
                nx_g.add_node(s,label=get_node_label(owl_graph,s, resolvers,language), shape="circle", color="lightblue", click=dict_to_html_table(get_node_literals(owl_graph, s, resolvers, language="en")))
        if t not in nx_g.nodes():
            if isAnonymous(t):
                nx_g.add_node(t,label="", shape="circle", color="white", click="")
            else:
                nx_g.add_node(t,label=get_node_label(owl_graph,t, resolvers,language), shape="circle", color="lightblue", click=dict_to_html_table(get_node_literals(owl_graph, t, resolvers, language="en")))

        nx_g.add_edge(s,t,label=get_node_label(owl_graph,l,resolvers,language),color="blue")

    for l,s,t in processed_lst_dplist:
        if s not in nx_g.nodes():
            if isAnonymous(s):
                nx_g.add_node(s,label="", shape="circle", color="white", click="")
            else:
                nx_g.add_node(s,label=get_node_label(owl_graph,s, resolvers,language), shape="circle", color="lightblue", click=dict_to_html_table(get_node_literals(owl_graph, s, resolvers, language="en")))
        if t not in nx_g.nodes():
            if isAnonymous(t):
                nx_g.add_node(t,label="", shape="circle", color="white", click="")
            else:
                nx_g.add_node(t,label=get_node_label(owl_graph,t, resolvers,language), shape="circle", color="lightblue", click=dict_to_html_table(get_node_literals(owl_graph, t, resolvers, language="en")))

        nx_g.add_edge(s,t,label=get_node_label(owl_graph,l,resolvers,language),color="red")

    return gv.convert.networkx_to_gjgf(nx_g)

