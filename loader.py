import serialization
import discourse
import rdflib
from rdflib import URIRef, Literal, Graph, Dataset
import uuid
from itertools import chain


import owlready2 as owlr


serial_onto_file = "Serialization.owl"
discourse_onto_file = "Discourse.owl"

try:
    serial = owlr.get_ontology(serial_onto_file).load()
except FileNotFoundError:
    serial = owlr.get_ontology("../" + serial_onto_file).load()

try:
    disco = owlr.get_ontology(discourse_onto_file).load()
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

def get_triples(dataset_object, serialization_graph_uri, serialization_name, data_rows, master_graph_uri):
    # Load Process Starts Here
    serialization_graph = dataset_object.graph(URIRef(serialization_graph_uri))
    S = serialization.Serialization(serialization_graph, serialization_name)
    temp_master = Graph() # Take offline copy of existing mastered triple set
    if master_graph_uri is None:
        gid = uuid.uuid4().hex
        master_graph = Graph(identifier=gid)
    else:
        master_graph = dataset_object.graph(URIRef(master_graph_uri))
    row_triples=[]
    for t in master_graph:
        temp_master.add(t)

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
    print(end_ts-start_ts, "for", len(data_rows) )


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

def load_to_graph(dataset_object, serialization_graph_uri, serialization_name, data_rows, master_graph_uri, discourse_graph_uri, title, metadata_payload, fingerprint_hashes=None, override_duplicate=False):
    start_ts = datetime.now()
    mastered_triples, entity_mappings = get_triples(dataset_object,serialization_graph_uri, serialization_name, data_rows, master_graph_uri)
    posits, declarations, discourse, disco_obj = generate_discourse(title, mastered_triples, metadata_payload)
    if fingerprint_hashes is not None:
        fingerprint = disco_obj.member_hash()
        if fingerprint in fingerprint_hashes:
            #This data has been uploaded previously
            if override_duplicate:
                # Get the existing discourse that contains the matching fingerprint to this one
                # and create a new discourse that points directly at that one
                print("doing this")

                alt_discourse_pointer = fingerprint_hashes[disco_obj.member_hash()]
                print(alt_discourse_pointer)

                print("Clearing members")
                disco_obj.clear_members()
                disco_obj.add_member(alt_discourse_pointer)
                print("now this")
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
    return True

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

