import owlready2 as owlr
import rdflib

import discourse

from rdflib import URIRef, Literal, Graph
from rdflib.term import _is_valid_uri
from rdflib.util import from_n3
from rdflib.namespace import RDF, RDFS
from rdflib import Namespace
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph

from collections import Counter
from itertools import chain
from datetime import datetime, timezone

import uuid

onto = owlr.get_ontology("datamodels_rdf.owl").load()
def flush(onto):
    for m in onto.Serialization.instances()[0].Contains:
        print(m, m.is_a)
flush(onto)
owlr.sync_reasoner(onto)

namespace = onto.base_iri

def datetime_literal(dt=None):
    if dt is None:
        dt_s = datetime.now(timezone.utc).strftime("%Y-%M-%dT%H:%M:%S")
    else:
        dt_s = dt.strftime("%Y-%M-%dT%H:%M:%S")
    return Literal(dt_s)


class Batch(object):
    def __init__(self, batch_name):
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace)
        self.type = URIRef(onto.BatchNode.iri)
        self.name = Literal(batch_name)
        self.label = Literal(f"{batch_name}_batch_{uid}")
        self.generated = datetime_literal()

    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, URIRef(onto.Name.iri), self.name),
                    (subj, URIRef(onto.GeneratedOn.iri), self.generated)
                    ]
        return triples


class Job(object):
    def __init__(self, job_name, batch_header):
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace)
        self.type = URIRef(onto.JobNode.iri)
        self.label = Literal(f"{job_name}_job_{uid}")
        self.name = Literal(job_name)
        self.generated = datetime_literal()
        self.MemberOf = batch_header

    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, URIRef(onto.Name.iri), self.name),
                    (subj, URIRef(onto.GeneratedOn.iri), self.generated),
                    (subj, URIRef(onto.MemberOf.iri), self.MemberOf.uri)
                    ]
        return triples

class Row(object):
    def __init__(self, row_number, job_header):
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace)
        self.type = URIRef(onto.RowNode.iri)
        self.label = Literal(f"row_{row_number}_{uid}")
        self.name = Literal(f"row_{row_number}")
        self.generated = datetime_literal()
        self.MemberOf = job_header

    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, URIRef(onto.Name.iri), self.name),
                    (subj, URIRef(onto.GeneratedOn.iri), self.generated),
                    (subj, URIRef(onto.MemberOf.iri), self.MemberOf.uri),
                    ]
        return triples


class Entity(object):
    def __init__(self,e_type,label,lineage=None):
        if lineage is None:
            lineage=label
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace)
        self.type = URIRef(e_type.iri)
        self.label = Literal(label)
        self.unique_label = Literal(lineage)
        self.data_properties=[]
        self.properties=[]

    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, URIRef(onto.UniqueIdentifier.iri), self.unique_label),
                    ]
        for p in self.data_properties:
            triples.append((subj, p[1], p[2]))
        for p in self.properties:
            triples.append((subj, p[1], p[2]))
        return triples

def serialize_row(row, serialization):
    entity_mappings = get_contents_matching_subclass(serialization, onto.EntityMapping)
    data_property_mappings = get_contents_matching_subclass(serialization, onto.DataPropertyMapping)
    property_mappings = get_contents_matching_subclass(serialization, onto.PropertyMapping)

    lineage_tree = {e.SerializationLabel.first():e.SerializationParentLabel.first() for e in entity_mappings}

    row_extracts = {}
    extracted_labels = {}
    for e in entity_mappings:
        # Create a dictionary containing raw Entity Objects in memory
        data_header = e.SerializationLabel.first()
        class_pointer = e.MappingMetaTarget.first()
        data = row.get(e.SerializationLabel.first())
        lineage = get_lineage(lineage_tree, e.SerializationLabel.first())
        lineage = ".".join([row.get(l) if row.get(l) is not None else "_" for l in lineage][::-1])
        if data is not None:
            row_extracts[data_header]=Entity(class_pointer, data, lineage)

    for d in data_property_mappings:

        subj = row_extracts.get(d.MappingDomain.first())
        if subj is not None:
            prop = URIRef(d.MappingMetaTarget.first().iri)
            if row[d.MappingRange.first()] is not None:
                obj = Literal(row[d.MappingRange.first()])
                subj.data_properties.append((d.name, prop, obj))

    for p in property_mappings:
        subj = row_extracts.get(p.MappingDomain.first())
        obj = row_extracts.get(p.MappingRange.first())
        if subj is not None and obj is not None:
            prop = URIRef(p.MappingMetaTarget.first().iri)
            subj.properties.append((p.name, prop, URIRef(obj.uri)))


    return list(chain (*[e.to_triples() for e in row_extracts.values()]))


def load_data(batch_name, batch_manifest=None, rdflib_graph=None):
    batch_header = Batch(batch_name)
    batch_discourse = discourse.Discourse(batch_header.name, is_proposed_by=batch_header.uri)

    if rdflib_graph is None:
        working_graph=Graph()
    else:
        working_graph=Graph()
        working_graph.parse ("datamodels_rdf.owl", format='xml')
        dmns = Namespace(onto.base_iri)
        working_graph.bind('dm', dmns, override=True, replace=True)
        discns = Namespace(discourse.onto.base_iri)
        working_graph.bind('disc', discns, override=True, replace=True)
        working_graph.bind('rdfs', RDFS)
        #namespace_d = {'dm': dmns, 'rdfs' : RDFS, 'rdf' : RDF}
        for t in rdflib_graph.triples((None, None, None)):
            working_graph.add(t)

    for t in batch_header.to_triples():
        working_graph.add(t)

    for job_def in batch_manifest:
        job_name, serial_choice, serialization_keys, data = job_def
        job_header = Job(job_name, batch_header)
        job_discourse = discourse.Discourse(job_header.name, is_proposed_by=job_header.uri)
        batch_discourse.members.append(job_discourse.uri)

        batch_header.Contains = job_header


        for t in job_header.to_triples():
            working_graph.add(t)


        for e, row in enumerate(data):
            row_facts=[]
            c_row = remap(row,serialization_keys)
            row_header = Row(e,job_header)
            for t in row_header.to_triples():
                working_graph.add(t)
            raw_row_triples = serialize_row(c_row, serial_choice)
            #print("r", len(raw_row_triples))

            mastered_row_triples = master_triples(working_graph, raw_row_triples)
            #print ("count of mastered_row_triples", len (mastered_row_triples))

            row_discourse = discourse.Discourse(row_header.name, is_proposed_by=row_header.uri)
            job_discourse.members.append(row_discourse.uri)

            for mt in mastered_row_triples:
                pp = discourse.Posit(mt)
                #row_facts.append(pp)
                working_graph.add(mt)

                if not pp.peek_longform(working_graph):
                    #print(len(t.to_triples()))
                    for pt in pp.to_triples():
                        working_graph.add(pt)
                else:
                    pp.update_uri_from_graph(working_graph)

                dec = discourse.Declaration(pp.uri)

                for dt in dec.to_triples():
                    working_graph.add(dt)

                row_discourse.members.append(dec.uri)


            for dt in row_discourse.to_triples():
                working_graph.add(dt)

            for t in row_header.to_triples():
                working_graph.add(t)

        for dt in job_discourse.to_triples():
            working_graph.add(dt)

    for dt in batch_discourse.to_triples():
        working_graph.add(dt)



    return working_graph







# =============================================
# ||                                         ||
# ||                                         ||
# ||       Utility Stuff                     ||
# ||                                         ||
# ||                                         ||
# =============================================

def master_triples(graph, triples):
    subj_unique_q = """SELECT distinct ?s ?u
    WHERE{
    ?s dm:UniqueIdentifier ?u .
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
