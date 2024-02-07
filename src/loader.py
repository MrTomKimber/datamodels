from models.core.serialization import serialization
from models.core.discourse import discourse
import rdflib
from rdflib import URIRef, Literal, Graph, Dataset
import uuid
from itertools import chain
import os
from math import e

import owlready2 as owlr

MODPATH=os.path.split(__file__)[0]
serial_onto_file = "Serialization.owl"
discourse_onto_file = "Discourse.owl"

try:
    serial = owlr.get_ontology(os.path.join(MODPATH,"models/core/serialization",serial_onto_file)).load()
except FileNotFoundError:
    serial = owlr.get_ontology("../" + serial_onto_file).load()

try:
    disco = owlr.get_ontology(os.path.join(MODPATH,"models/core/discourse",discourse_onto_file)).load()
except FileNotFoundError:
    disco = owlr.get_ontology("../" + discourse_onto_file).load()

from datetime import datetime

# Loader - using the following pattern...
# 1. Using a referenced Serialization definition
# 2. Load data from a serialized file
# 3. Generate a set of unmastered triples
# 4. Using a pointer for a set of triple masteres
# 5. Using a pointer for a target location.
# 6. Create set of new master triples for inclusion into master
# 7. Create set of new discourse triples for inclusion into target
# 8. With some standardised meta-data to be applied at runtime.
# 9. Apply triple sets to their target locations.

def get_triples(dataset_object, serialization_graph_uri, serialization_reference, data_rows, master_graph_uri):
    # Load Process Starts Here
    serialization_graph = dataset_object.graph(URIRef(serialization_graph_uri))
    S = serialization.Serialization(serialization_graph, serialization_reference)
    temp_master = Graph() # Take offline copy of existing mastered triple set
    if master_graph_uri is None:
        gid = uuid.uuid4().hex
        master_graph = Graph(identifier=gid)
    else:
        master_graph = dataset_object.graph(URIRef(master_graph_uri))
    row_triples=[]
    for t in master_graph:
        temp_master.add(t)
    print("//////LOCATE1/////")
    # Cycle over data rows, and using the appropriate Serialization, convert to a set of
    # Mastered triples, ready to add to the master dataset.
    e=0
    f=0
    e_mappings={}
    start_ts = datetime.now()
    for row in data_rows:
        e=e+1
        new_triples, e_mappings = S.extract_raw_triples(row, e_mappings)
        row_triples.extend (new_triples)

    row_triples = set(S.master_triples(temp_master, row_triples))

    end_ts = datetime.now()
    print(end_ts-start_ts, "for", len(row_triples), "from", len(data_rows) )
    print("//////LOCATE2/////")

    try:
        mgid = master_graph._Graph__get_identifier()
    except AttributeError:
        mgid = master_graph._Graph__identifier
    triples = [(s,p,o) for s,p,o in row_triples]

    return triples, e_mappings


# Given a discourse name, a set of mastered triples and some payload duals
# Create all the required triples to express a discourse, set of declarations, posits and links to mastered triples
# Returns posit_triples
#         declaration_triples
#         discourse_triples

def generate_discourse(d_name, triples, payload):
    posits = set()
    declarations = set()
    for triple in triples:
        t_pos = discourse.Posit(triple)
        posits.add(t_pos)
        t_dec = discourse.Declaration(t_pos.uri, asserts=True)
        declarations.add(t_dec)

    t_disc = discourse.Discourse(d_name, payload)
    for t_dec in declarations:
        t_disc.add_member(t_dec, t_dec.asserts)

    #triples = set([(s,p,o) for s,p,o in triples])
    posit_triples = set(chain(*[p.to_triples() for p in posits]))

    declaration_triples = set(chain(*[p.to_triples() for p in declarations]))
    discourse_triples = set(t_disc.to_triples())

    # Need to return separate sets of triples, or attach quad graph names to these ones so they can be
    # separated out later.
    return posit_triples, declaration_triples, discourse_triples, t_disc

def triples_to_quads(triples, graph_uri="http://master"):
    for s,p,o, *_ in triples:
        yield (s,p,o,URIRef(graph_uri))

def diffset(S1, S2):
    # Given two input sets, s1 and s2, return the Left difference, Intersection and Right difference between them
    L = S1.difference(S2)
    I = S1.intersection(S2)
    R = S2.difference(S1)
    return L,I,R

def sigmoid(x):
    return 1/(1+(e**(-10*(x-0.5))))

def score_diffset(S1,S2):
    l,i,r = diffset(S1, S2)
    ll,il,rl = len(l), len(i), len(r)
    pos=(0.1*ll)+il+(0.6*rl)
    return sigmoid(pos/(ll+il+rl))
    

def match_serialization_from_columns(dataset_object, serialization_graph_uri, column_set):
    threshold=0.95
    rs = dataset_object.query("""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
    PREFIX owl: <http://www.w3.org/2002/07/owl#> 
    PREFIX ser: <http://www.tkltd.org/ontologies/serialization#> 
    select ?s ?p ?o
    WHERE { GRAPH <http://config> { ?m ?p ?o. 
    ?m ser:IsComponentOfSerialization ?s. 
    VALUES ?p { ser:MappingDomain ser:MappingRange ser:SerializationLabel ser:SerializationParentLabel}}}""")

    ser_label_set = set([(s.toPython(), o.toPython()) for s,p,o in rs])
    ser_label_d = dict()
    for s,o in ser_label_set:
        if s in ser_label_d.keys():
            ser_label_d[s].add(o)
        else:
            ser_label_d[s]=set([o])
    matching_ser_scores = dict()
    for k,v in ser_label_d.items():
        score=score_diffset(column_set, v)
        if score>threshold:
            matching_ser_scores[k]=score
    
    if len(matching_ser_scores)==1:
        return set(matching_ser_scores.keys()).pop()
    elif len(matching_ser_scores)>1:
        return sorted([(k,v) for k,v in matching_ser_scores.items()], key=lambda x : x[1])[-1]
    raise ValueError(f"No matching serialization found for columns {set(column_set)}")



def load_to_graph(dataset_object, serialization_graph_uri, serialization_reference, data_rows, master_graph_uri, discourse_graph_uri, title, metadata_payload, fingerprint_hashes=None, override_duplicate=False):
    start_ts = datetime.now()
    mastered_triples, entity_mappings = get_triples(dataset_object, serialization_graph_uri, serialization_reference, data_rows, master_graph_uri)

    posits, declarations, discourse, disco_obj = generate_discourse(title, mastered_triples, metadata_payload)
    if fingerprint_hashes is not None:
        fingerprint = disco_obj.member_hash()
        if fingerprint in fingerprint_hashes:
            #This data has been uploaded previously
            if override_duplicate:
                # Get the existing discourse that contains the matching fingerprint to this one
                # and create a new discourse that points directly at that one
                
                alt_discourse_pointer = fingerprint_hashes[disco_obj.member_hash()]

                disco_obj.clear_members()
                disco_obj.add_member(alt_discourse_pointer)
                
                discourse = disco_obj.to_triples()
                posits = set()
                declarations = set()

            else:
                print("This data is already loaded! - Aborting")
                return None
    dataset_object.addN(triples_to_quads(mastered_triples, URIRef(master_graph_uri)))
    dataset_object.addN(triples_to_quads(posits, URIRef(discourse_graph_uri)))
    dataset_object.addN(triples_to_quads(declarations, URIRef(discourse_graph_uri)))
    dataset_object.addN(triples_to_quads(discourse, URIRef(discourse_graph_uri)))
    triple_count = len(mastered_triples)+len(posits)+len(declarations)+len(discourse)
    end_ts = datetime.now()
    print(end_ts-start_ts, "for", triple_count, "triples" )
    return (fingerprint, disco_obj.uri)

def master_on_predicate_g(master_q, process_q, predicate=None):
    # Compare process_q against content in master_q and return mastered_q
    m_lengths = set([len(c) for c in master_q])
    p_lengths = set([len(c) for c in master_q])
    if predicate is None:
        predicate_uri = URIRef(serial.UniqueIdentifier.iri)
    else:
        if isinstance(predicate, rdflib.term.URIRef):
            predicate_uri = predicate
        else:
            predicate_uri = URIRef(predicate)
    if m_lengths != p_lengths:
        assert False
    if m_lengths=={3}:
        triples=True
    elif m_lengths=={4}:
        quads=True
    else:
        assert False
    start_ts = datetime.now()
    if quads:
        master_lookup = { o:s for s,p,o,g in master_q if p==predicate_uri}
        process_lookup =  { o:s for s,p,o,g in process_q if p==predicate_uri}
        conversion_lookup = { vp : master_lookup.get(kp,kp) for kp,vp in process_lookup.items()}
        mastered_q = [(conversion_lookup.get(s,s), conversion_lookup.get(p,p), conversion_lookup.get(o,o), conversion_lookup.get(g,g)) for s,p,o,g in process_q]
    elif triples:
        master_lookup = { o:s for s,p,o in master_q if p==predicate_uri}
        process_lookup =  { o:s for s,p,o in process_q if p==predicate_uri}
        conversion_lookup = { vp : master_lookup.get(kp,kp) for kp,vp in process_lookup.items()}
        mastered_q = [(conversion_lookup.get(s,s), conversion_lookup.get(p,p), conversion_lookup.get(o,o)) for s,p,o in process_q]
    end_ts = datetime.now()


    return mastered_q

