
import pandas as pd
import owlready2 as owlr
#https://pythonhosted.org/Owlready/
import rdflib
from rdflib import URIRef, Literal, Graph
from rdflib.namespace import RDF, RDFS
from rdflib import Namespace
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph

from collections import Counter
import uuid

import networkx as nx
from datetime import datetime, timezone

def master_triples(onto, graph, triples):
    subj_unique_q = """SELECT distinct ?s ?u
    WHERE{
    ?s dm:UniqueIdentifier ?u .
    ?f ?p ?s .
    }"""
    source_dict = dict([(k,v) for v,k in list(graph.query(subj_unique_q))])

    t_graph = Graph()
    t_graph.parse ("datamodels_rdf.owl", format='xml')
    dmns = Namespace(onto.base_iri)
    t_graph.bind('dm', dmns, override=True, replace=True)
    t_graph.bind('rdfs', RDFS)
    for t in triples:
        t_graph.add(t)
    target_dict = dict([(k,v) for v,k in list(t_graph.query(subj_unique_q))])
    switch_dict = {v:source_dict.get(k,v) for k,v in target_dict.items()}

    new_triples = []
    for s,p,o in triples:
        if not(s,p,o) in graph:
            new_triples.append((switch_dict.get(s,s), switch_dict.get(p,p), switch_dict.get(o,o)))

    return new_triples

def load_data(onto, batch_manifest=None, rdflib_graph=None, serial_key=None):
    # Batch Manifest is a dictionary containing a set of file handles, and the serialization methods to be used to process them
    namespace = onto.base_iri

    for job in batch_manifest.items():
        serial_choice , data = job
        entities = get_contents_matching_subclass(serial_choice, onto.EntityMapping)
        data_properties = get_contents_matching_subclass(serial_choice, onto.DataPropertyMapping)
        properties = get_contents_matching_subclass(serial_choice, onto.PropertyMapping)

        lineage_tree = {e.SerializationLabel.first():e.SerializationParentLabel.first() for e in entities}


        triples =  []
        catalog = {}

        batch_header_URI, header_triples = gen_batch_header(onto, onto.iri, "conceptual model data load")
        triples.extend( header_triples )

        job_header_URI, job_triples = gen_job_header(onto, batch_header_URI, onto.iri, "conceptual_entity_load")
        triples.extend( job_triples )

        reify_triples=[]

        for e, row in enumerate(data):
            row_header, row_h_triples = gen_row_header(onto, job_header_URI, onto.iri, f"data_row_{e}")
            for t in row_h_triples:
                if t not in triples:
                    triples.append( t )
        #    print(row)
            row_triples, catalog = gen_content(onto, row_header, remap(row, serial_key), entities, properties, data_properties, lineage_tree,catalog, namespace)

            dup_index=[]
            for t in row_triples:
                if t not in triples:
                    triples.append( t )
                    dup_index.append(True)
                else:
                    dup_index.append(False)

            for i,individual in enumerate(row_triples):
                if dup_index[i]:
                    reify_triples.extend(reify_triple(onto, row_header, individual))

        # Reify triples to the Row_Node:
        #print (len(triples), len(reify_triples))

        triples.extend(reify_triples)

        triples = master_triples(onto, rdflib_graph, triples)

        for e,t in enumerate(triples):
            try:
                rdflib_graph.add(t)
            except AssertionError as err:
                print(e, t)
                print(err)
            rdflib_graph.add(t)



    return rdflib_graph



# Collect mappings from a given serializatin
def get_contents_matching_subclass(s, subclass):
    m_list = []
    if not isinstance(subclass, list):
        subclass = [subclass]
    for m in s.Contains:
        if any([(c in subclass or x in subclass) for c in m.is_a for x in m.is_a.first().is_a]):
            m_list.append(m)
    return m_list

def get_schema_labels(s, onto):
    labels=[]
    for m in get_contents_matching_subclass(s,[onto.EntityMapping]):
        #print(m)
        if len(m.SerializationLabel)>0:
            labels.extend(m.SerializationLabel)

    for m in get_contents_matching_subclass(s,[onto.DataPropertyMapping]):
        #print(m)
        if len(m.MappingRange)>0:
            labels.extend(m.MappingRange)

    return labels


def remap(d, mapper):
    return {v:d.get(k) for k,v in mapper.items()}




def get_lineage(d, l, acc=None):
    if acc is None:
        if l is not None:
            acc=[l]
    q = d.get(l)
    if q is not None:
        acc.append(q)
        acc = get_lineage(d, q, acc)
    return acc




def gen_batch_header(onto, namespace, name):
    bh_type = onto.BatchNode
    key = uuid.uuid4().hex
    now = datetime.now(timezone.utc).strftime("%Y-%M-%dT%H:%M:%S")
    subj = URIRef(key, namespace)
    props = { RDF.type : URIRef(bh_type.iri),
              RDFS.label : Literal(name),
              URIRef(onto.GeneratedOn.iri) : Literal(now) }
    triples=[]
    for k,v in props.items():
        triples.append((subj, k, v))
    return subj, triples

def gen_job_header(onto, batch_header_URI, namespace, serialization_name):
    jh_type = onto.JobNode
    key = uuid.uuid4().hex
    now = datetime.now(timezone.utc).strftime("%Y-%M-%dT%H:%M:%S")
    subj = URIRef(key, namespace)
    props = { URIRef(onto.MemberOf.iri) : batch_header_URI,
              RDF.type : URIRef(jh_type.iri),
              RDFS.label : Literal(serialization_name),
              URIRef(onto.GeneratedOn.iri) : Literal(now) }

    triples=[]
    rev_props = [(batch_header_URI, URIRef(onto.Contains.iri), subj)]

    for k,v in props.items():
        triples.append((subj, k, v))
    triples.extend(rev_props)
    return subj, triples

def gen_row_header(onto, job_header_URI, namespace, serialization_name):
    rh_type = onto.RowNode
    key = uuid.uuid4().hex
    now = datetime.now(timezone.utc).strftime("%Y-%M-%dT%H:%M:%S")
    subj = URIRef(key, namespace)
    props = { URIRef(onto.MemberOf.iri) : job_header_URI,
              RDF.type : URIRef(rh_type.iri),
              RDFS.label : Literal(serialization_name),
              URIRef(onto.GeneratedOn.iri) : Literal(now) }
    rev_props = [(job_header_URI, URIRef(onto.Contains.iri), subj)]
    triples=[]
    for k,v in props.items():
        triples.append((subj, k, v))
    triples.extend(rev_props)
    return subj, triples



# Generate the s,p,o triples for a single row of data
# Additionally, link each triple component (s,p,o) to a unique row_id, to enable retrieval at row-level

def reify_triple(onto, collection_node, triple):
    triples = []
    namespace = onto.iri
    uid = uuid.uuid4().hex
    unique_id = URIRef(uid, namespace)
    fact_links=[]
    fact_links.append( (unique_id, RDF.type,URIRef(onto.FactNode.iri)))
    fact_links.append( (unique_id, RDFS.label, Literal(f"fact_{uid}")))
    fact_links.append ((unique_id, URIRef(onto.MemberOf.iri),collection_node))
    fact_links.append ((collection_node, URIRef(onto.Contains.iri),unique_id))
    triples.extend(fact_links)
    #print(triple)
    s,p,o = triple
    triples.append((unique_id, URIRef(onto.FactSubject.iri),s))
    triples.append((unique_id, URIRef(onto.FactPredicate.iri),p))
    triples.append((unique_id, URIRef(onto.FactObject.iri),o))
    return triples

def gen_content(onto, row_header_URI, row, entities, properties, data_properties, lineage_tree, batch_catalog, namespace):
    triples = []
    top_level_objects = {}
    label_d = {}
    for e in entities:
        key = uuid.uuid4().hex
        subj = e.SerializationLabel.first()

        e_type = e.MappingMetaTarget.first()
        data = row.get(e.SerializationLabel.first())
        #print ( e, subj, data, e_type)
        if data is not None:
            if data not in batch_catalog:
                batch_catalog[data]=URIRef(key, namespace)
                label_d[subj]=URIRef(key, namespace)
            else:
                label_d[subj]=batch_catalog[data]


            subj=label_d[e.SerializationLabel.first()]
            props = { RDF.type : URIRef(e_type.iri),
                                  RDFS.label : Literal(data)}
            top_level_objects[data]=None

            for k,v in props.items():
                triples.append([subj, k, v])

    for d in data_properties:
        subj = label_d.get(d.MappingDomain.first())
        if subj is not None:
            prop = URIRef(d.MappingMetaTarget.first().iri)
            obj = Literal(row[d.MappingRange.first()])
            triples.append((subj, prop, obj))

    for p in properties:
        subj = label_d.get(p.MappingDomain.first())
        if subj is not None:
            prop = URIRef(p.MappingMetaTarget.first().iri)

    #        obj = Literal(row[p.MappingRange.first()])
            #print(p.MappingRange.first())
            obj = label_d.get(p.MappingRange.first())
            #print(subj,p, obj)
            if obj is not None:
                triples.append((subj, prop, obj))

    for e in entities:
        if row.get(e.SerializationLabel.first()) is not None:
            lineage = get_lineage(lineage_tree, e.SerializationLabel.first())
            lineage = ".".join([row.get(l) if row.get(l) is not None else "_" for l in lineage][::-1])

            #print("\t", e.MappingMetaTarget.first(), lineage)
            subj = label_d.get(e.SerializationLabel.first())
            if subj is not None:
                prop = URIRef(onto.UniqueIdentifier.iri)
                obj = Literal(lineage)
                triples.append((subj, prop, obj))
                top_level_objects[subj]=lineage
    return triples, batch_catalog
