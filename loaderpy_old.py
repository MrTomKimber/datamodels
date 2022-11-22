
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

def gen_temp_entity_triples_from_row(s_mappings, onto_map, namespace, row, row_id):

    object_triples=[]
    row_node_uri = URIRef(uuid.uuid4().hex, namespace)
    rne = URIRef(onto_map['isRowNode'][0].iri)
    rnp = URIRef(onto_map['isParticipant'][0].iri)

    row_node_triple = (row_node_uri, RDF.type, rne)
    row_node_identifier_p = URIRef(onto_map['UniqueIdentifier'][0].iri)
    row_node_identifier_triple = (row_node_uri, row_node_identifier_p, Literal(row_id))

    for m_key, m_d in s_mappings.items():
        #print(m_key, m_d)
        if m_d['MappingSubType']=="Entity":
#            print("Create Temporary Entity")
            if m_d['SerializationLabel'] in row:
                data = row[m_d['SerializationLabel']]
                e_type = onto_map[m_d['MappingLabel']]
#                print(e_type[0], ":", data)
                key = uuid.uuid4().hex
                thing_URI = URIRef(key, namespace)
                # RDF:type, RDFS:label
                props = { RDF.type : URIRef(e_type[0].iri),
                          RDFS.label : Literal(data)}

                for k,v in props.items():
                    object_triples.append((thing_URI, k, v))
#                print()

    object_triples.append(row_node_triple)



# Create a graph containing the newly created object_triples
    row_g = rdflib.Graph()

    for triple in object_triples:
#        print(triple)
        row_g.add(triple)

    property_triples=[]
    property_triples.append(row_node_identifier_triple)

    # Assign all objects downstream of RowNodeParticipant
    for s,p,o in object_triples:
        property_triples.append((row_node_uri, rnp, s))


    for m_key, m_d in s_mappings.items():
        #print(m_key, m_d)
        if m_d['MappingSubType']=="Property":
#            print("Create Property Link")
            if m_d['SerializationLabel'] in row:
                data = row[m_d['SerializationLabel']] # Get the value in the row - normally the target object label
                prop = onto_map[m_d['MappingLabel']][0] # Get the property being referenced
                prop_domain = onto_map[m_d['MappingDomain']][0] # Get the domain class (used for search in the graph)
                prop_range = onto_map[m_d['MappingRange']][0] # Get the range class (used for search)
                prop_type = onto_map[m_d['MappingRange']][1]
#                print("!", prop, prop_domain, prop_range, prop_type)
                prop_iri = URIRef(prop.iri)
                subj_node = get_thing_from_label_graphsearch(row_g, prop_domain, search_key=None)[0]
                if prop_type == "class":
                    print(row_g, prop_range, data)
                    obj_node = get_thing_from_label_graphsearch(row_g, prop_range, search_key=data)[0]
                elif prop_type == "data" :
                    obj_node = Literal(data)
#                print ("triple", subj_node, prop_iri, obj_node)
                property_triples.append((subj_node, prop_iri, obj_node))



#    for triple in property_triples:
#        print(triple)
#        row_g.add(triple)

    # Now there exist object_triples, property_triples
    # Additionally, we want some extra ontology driven triples for uniqueidentifiers
    # build from the row-level class hierarchy


    #return row_g
    return object_triples + property_triples


def t2rdflibg(triples): #triples to rdflib graph
    g = rdflib.Graph()
    for t in triples:
        g.add(t)
    return g

def get_key_values(g, key=RDFS.label, invert=False):
    if not invert:
        return list([(s, o.value) for s,p,o in g.triples((None, key, None))])
    else:
        return list([(o.value,s) for s,p,o in g.triples((None, key, None))])



def get_thing_from_label_graphsearch(graph, domain=None, search_key=None):
    #sd_list = [c for c in list(space.classes()) if c==domain]

    if domain is not None:

        sd_list = [s for s,p,o in graph.triples((None, RDF.type, URIRef(domain.iri)))]
    else:
        sd_list = [s for s,p,o in graph.triples((None, RDF.type, None))]
#    print("sd_list:", sd_list)
    # Get instances of classes that match provided keys
    if search_key is None:
        c_s = [s for s in sd_list]
    else:
        c_s = [s for l in sd_list for s,p,o in graph.triples((None, RDFS.label, Literal(search_key)))]

    return c_s

def search_on_key_value(graph, namespace_d, key, search):
    search= str(search)
    sparql_base = """SELECT distinct ?s
    WHERE
        {
        ?s %%key%% ?q FILTER ( ?q = str("%%search%%") ) .
        }""".replace("%%search%%",search).replace("%%key%%", key)

    matches = graph.query(sparql_base, initNs=namespace_d)
    return matches

def text_process(text):
    return text.lower().replace(" ", "_")

# Traverse a graph g, from some source s and generate a list of all precursor items.
def nx_walk_predecessors(g,s,l=None,invert=False,process=None):
    if l is None:
        l=[]
    nxt=list(g.predecessors(s))

    if process is None:
        p_s=s
    else:
        p_s=process(s)

    if len(nxt)>0:

        l.extend([p_s])

        for n in nxt:

            nx_walk_predecessors(g,n,l,process=process)
    else:
        l.extend([p_s])
    if invert:
        return l[::-1]
    else:
        return l

# Prepare Unique Identity Annotation Triples
# Get container tree
def gen_unique_identity_triples(graph, namespace_d):

    # This query looks for nodes that are linked by merit of dm:HierarchicalRelations
    row_hierarchy_sparql="""SELECT distinct ?sl ?ol
    WHERE

    {

         {?s ?p ?o .
         ?p rdfs:subPropertyOf dm:HierarchicalRelations.
         ?s rdfs:label ?sl .
         ?o rdfs:label ?ol .
         }

         }

     """


    get_s_nodes="""
    SELECT ?s ?q ?l
    WHERE
        {
        ?s ?p ?o.
        ?o rdfs:subClassOf dm:Definition.
        BIND ( rdf:type as ?p )
        BIND ( dm:UniqueIdentifier as ?q)
        ?s rdfs:label ?l
        }

    """

    ng = nx.DiGraph()

    c_tree = list(graph.query(row_hierarchy_sparql, initNs=namespace_d))
    print(c_tree)

    for e in [(e[0].value, e[1].value)  for e in c_tree ]:
        ng.add_edge(*e)

#    source = [n for n,d in  ng.out_degree() if d==0][0]

    unique_id_triples = []
    for uri, prop, lab in list(graph.query(get_s_nodes, initNs=namespace_d)):
        unique_id_triples.append((uri, prop, Literal(".".join(nx_walk_predecessors(ng,lab.value,invert=True,process=text_process)))))

    return unique_id_triples
