import owlready2 as owlr
import rdflib
from rdflib import URIRef, Literal, Graph
from rdflib.term import _is_valid_uri
from rdflib.util import from_n3
from rdflib.namespace import RDF, RDFS
from rdflib import Namespace
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph

import graphviz
import pandas as pd
from collections import Counter
from itertools import chain
from datetime import datetime, timezone
import uuid

import discourse



onto = owlr.get_ontology("datamodels_rdf.owl").load()
def flush(onto):
    for m in onto.Serialization.instances()[0].Contains:
        print(m, m.is_a)
flush(onto)
owlr.sync_reasoner(onto)

namespace = onto.base_iri

def spawn_rdflib_graph():
    # Create Empty Graph and populate it with required ontologies
    graph = Graph()
    graph.parse ("datamodels_rdf.owl", format='xml')
    graph.parse ("discourse.owl", format='xml')
    dmns = Namespace(onto.base_iri)
    graph.bind('dm', dmns, override=True, replace=True)
    discns = Namespace(discourse.onto.base_iri)
    graph.bind('disc', discns, override=True, replace=True)
    graph.bind('rdfs', RDFS)
    return graph
    #namespace_d = {'dm': dmns, 'rdfs' : RDFS, 'rdf' : RDF}

def copy_rdflib_graph(g, master=None):
    c = Graph()
    for t in g.triples((None, None, None)):
        c.add(t)
    for ns in g.namespaces():
        c.bind(*g, override=True, replace=True)
    return c


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

    entity_mappings = onto_get_contents_matching_subclass(serialization, onto.EntityMapping)
    data_property_mappings = onto_get_contents_matching_subclass(serialization, onto.DataPropertyMapping)
    property_mappings = onto_get_contents_matching_subclass(serialization, onto.PropertyMapping)

    # Label : ParentLabel dictionary for building unique keys from chained concepts
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


def old_serialize_row(row, serialization):
    entity_mappings = onto_get_contents_matching_subclass(serialization, onto.EntityMapping)
    data_property_mappings = onto_get_contents_matching_subclass(serialization, onto.DataPropertyMapping)
    property_mappings = onto_get_contents_matching_subclass(serialization, onto.PropertyMapping)

    # Label : ParentLabel dictionary for building unique keys from chained concepts
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
        working_graph=spawn_rdflib_graph()
    else:
        working_graph=spawn_rdflib_graph()
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

    all_is_well = True
    if all_is_well:
        for t in working_graph.triples((None, None, None)):
            if t not in rdflib_graph.triples((t[0], t[1], t[2])):
                rdflib_graph.add(t)

    return rdflib_graph







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
    # Make a temporary graph of the new set of triples
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
def onto_get_contents_matching_subclass(s, subclass):
    m_list = []
    if not isinstance(subclass, list):
        subclass = [subclass]
    for m in s.Contains:
        if any([(c in subclass or x in subclass) for c in m.is_a for x in m.is_a.first().is_a]):
            m_list.append(m)
    return m_list

def onto_get_schema_labels(s, onto):
    labels=[]
    for m in onto_get_contents_matching_subclass(s,[onto.EntityMapping]):
        #print(m)
        if len(m.SerializationLabel)>0:
            labels.extend(m.SerializationLabel)

    for m in onto_get_contents_matching_subclass(s,[onto.DataPropertyMapping]):
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


# =============================================
# ||                                         ||
# ||                                         ||
# ||       Reporting and                     ||
# ||          sparql queries                 ||
# ||                                         ||
# =============================================


def report_object_type_counts(graph):
    data_load_objects_sparql = """
    SELECT (count(?s) as ?count) ?t
    WHERE
        {
            ?s a ?t .
        }
    GROUP BY ?t
    """
    results = graph.query(data_load_objects_sparql)
    return results

def report_batch_node_names(graph):
    q="""SELECT ?batch_node ?batch_name
    WHERE {
        ?batch_node a dm:BatchNode.
        ?batch_node dm:Name ?batch_name
    }"""
    batch_nodes = list(graph.query(q))
    return batch_nodes

def report_digests_from_discourse(graph, batch_node_uri):
    # Retrieve s,p,o digests from declared posits linked to individual data loads.

    discourse_q = """       SELECT ?digest
                            WHERE
                                {
                                    BIND (%%bn%% as ?batch_node).
                                    ?job_node dm:MemberOf ?batch_node.
                                    ?row_node dm:MemberOf ?job_node.
                                    ?row_node disc:Proposes ?discourse.
                                    ?discourse disc:DiscourseContains ?decl.
                                    ?decl disc:Posits ?p.
                                    ?p disc:Digest ?digest
                                }
                            """

    qq = discourse_q.replace("%%bn%%", batch_node_uri)
    results = graph.query(qq)
    return results

def convert_longform_to_triples(results):
    return [discourse.longform_to_triple(r[0]) for r in results]


def report_and_generate_diagram(graph, batch_node_uri, graphviz_engine="dot"):
    digests = report_digests_from_discourse(graph, batch_node_uri)
    ent_graph = spawn_rdflib_graph()

    b_entities_q = """
    SELECT ?s ?p ?o
    WHERE{
        {
        VALUES ?ent_types { dm:ModelDomain dm:Model dm:Class dm:Context  }
        VALUES ?p { rdf:type rdfs:label }
        ?s a ?ent_types.
        ?s ?p ?o.
        }

    }
    """

    b_rels_q = """
    SELECT ?from ?froml ?rel ?to ?tol ?rel_from_card ?rel_to_card
    WHERE{
        {
            ?from ^dm:RelationshipFromClass/dm:RelationshipToClass  ?to .
            ?from rdfs:label ?froml.
            ?to rdfs:label ?tol.
            ?r dm:RelationshipToClass ?to.
            ?r rdfs:label ?rel .
            ?r a dm:Relationship .
            BIND (?rel as ?p)
            OPTIONAL {?r dm:ToCardinality ?rel_to_card}
            OPTIONAL {?r dm:FromCardinality ?rel_from_card}
        }

    }
    """

    b_entities_results = graph.query(b_entities_q)
    b_rels_results = graph.query(b_rels_q)

    ents_df = pd.DataFrame(b_entities_results, columns=['s','p','o']).sort_values(by='s')#.groupby(1)
    ents_df = ents_df.pivot(index='s', columns='p')#.reset_index()
    flat_cols = ['_'.join(col).split("#")[1] for col in ents_df.columns.values]
    ents_df.columns=flat_cols
    ents_df['type']=ents_df['type'].apply(lambda x : x.split("#")[1])
    ents_df=ents_df.sort_values(by='type')

    ents_df = ents_df[ents_df['type']=="Class"]
    cardinality_codes = {"One" : "1",
                         "Many" : "M",
                         "None": ""}

    b_rels_df = pd.DataFrame(b_rels_results, columns=["from", "froml", "rel", "to", "tol", "fromcard", "tocard"])
    b_rels_df["fromcard_"]=b_rels_df["fromcard"].apply(lambda x : cardinality_codes.get(str(x)))
    b_rels_df["tocard_"]=b_rels_df["tocard"].apply(lambda x : cardinality_codes.get(str(x)))

    print(b_rels_df)

    gv_graph = graphviz.Digraph(name="pdp_graph", engine=graphviz_engine)

    for i,e in b_rels_df.iterrows():
        edge, edge_kwargs = (e['froml'], e['tol']), {"label":e['rel'], "headlabel":e['tocard_'], "taillabel":e['fromcard_']}
        gv_graph.edge(*edge, **edge_kwargs)

    for i,n in ents_df.iterrows():
        node, node_kwargs = n['label'], {"type":n['type']}
        gv_graph.node(node, **node_kwargs)

    return gv_graph
