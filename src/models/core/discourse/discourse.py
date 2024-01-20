from typing import Optional

import owlready2 as owlr
import rdflib
from rdflib import URIRef, Literal, Graph
from rdflib.term import _is_valid_uri
from rdflib.util import from_n3
from rdflib.namespace import RDF, RDFS
from rdflib import Namespace
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from collections import Counter
import uuid
from datetime import datetime, timezone
import hashlib
import os

MODPATH=os.path.split(__file__)[0]

def uuid_format(hx):
    return hx[0:12]+"-"+hx[12:16]+"-"+hx[16:20]+"-"+hx[20:]

def datetime_literal(dt=None):
    if dt is None:
        dt_s = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    else:
        dt_s = dt.strftime("%Y-%m-%dT%H:%M:%S")
    return Literal(dt_s)

def triple_to_longform(rdf_triple):
    return "~~~".join([t.n3() for t in rdf_triple])

def n3_to_term(n3):
    return from_n3(n3.encode('unicode_escape').decode('unicode_escape'))



def longform_to_triple(longform):
    if isinstance(longform, rdflib.Literal):
        longform=longform.toPython()
    if all([c=='"' for c in [longform[0], longform[-1]]]):
        print(longform)
        longform=longform[1:-1]
    s,p,o = [n3_to_term(t) for t in longform.split("~~~")]
    return tuple((s,p,o))

try:
    disco = owlr.get_ontology(os.path.join(MODPATH,"Discourse.owl")).load()
except FileNotFoundError:
    disco = owlr.get_ontology("../Discourse.owl").load()
namespace = disco.base_iri

serial_onto_file = "Serialization.owl"

try:
    serial = owlr.get_ontology(os.path.join(MODPATH,"../serialization", serial_onto_file)).load()
except FileNotFoundError:
    serial = owlr.get_ontology("../" + serial_onto_file).load()

class Posit(object):
    def __init__(self, triple):
        s,p,o = triple
        #uid = uuid.uuid4().hex
        #self.uri = URIRef(uid, namespace+"#")
        self.type = URIRef(disco.Posit.iri)

        self.longform = Literal(triple_to_longform(triple ))
        uid = uuid_format(hashlib.md5(self.longform.n3().encode("utf-8")).hexdigest())
        self.uid = Literal(uid)
        self.uri = URIRef(uid, namespace+"#")
        self.label = Literal(f"posit_{uid}")
        self.subject = s
        self.predicate = p
        self.object = o

    # Where a Posit turns out to already exist in the graph,
    # use this method to edit the uri of this representation
    # to align it to the graph
    def update_uri_from_graph(self, graph):
        search = list(graph.triples((None,URIRef(disco.Digest.iri), self.longform)))
        if len(search) > 0 :
            longform = search[0][0]
        else:
            assert False
        self.uri=longform
        return self.uri

    def peek_triples(self, graph): # Does the triples referenced by this posit exist already within the graph?
        s,p,o = self.subject, self.predicate, self.object
        #print (len (list(graph.triples((s,p,o)))))
        if len (list(graph.triples((s,p,o))))>0:
            return True
        else:
            return False

    def peek_longform(self, graph): # Does the posit identified by the longform already exist in the graph?
        s,p,o = self.subject, self.predicate, self.object
        #print (len (list(graph.triples((None,URIRef(onto.Digest.iri), self.longform)))))
        if len (list(graph.triples((None,URIRef(disco.Digest.iri), self.longform))))>0:
            return True
        else:
            return False

    def poke(self, graph, allow_duplicate=False): # Push the triples referenced by this posit into the graph
        if allow_duplicate or not self.peek_longform(graph):
            graph.add((self.s, self.p, self.o))
        else:
            pass

    def repoint(self, repoint_dict): # Translate the posit from one set of terms to another via a mapping dict
        changes = [False,False,False]
        if self.subject in repoint_dict.keys():
            self.subject = repoint_dict[self.subject]
            changes[0] = True

        if self.predicate in repoint_dict.keys():
            self.predicate = repoint_dict[self.predicate]
            changes[1] = True

        if self.object in repoint_dict.keys():
            self.object = repoint_dict[self.object]
            changes[2] = True
        return changes

    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, URIRef(disco.Subject.iri), self.subject),
                    (subj, URIRef(disco.Predicate.iri), self.predicate),
                    (subj, URIRef(disco.Object.iri), self.object),
                    (subj, URIRef(disco.Digest.iri), self.longform),
                    (subj, URIRef(serial.UniqueIdentifier.iri), self.uid)
                    ]
        return triples


class Declaration(object):

    def __init__(self, posit_uri, asserts : Optional[bool]=None):
        # Asserts flag is used to either positively Assert, negatively Refute, or neutrally Posit
        # asserts expects a boolean value
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace+"#")
        self.type = URIRef(disco.Declaration.iri)
        self.label = Literal(f"declaration_{uid}")
        self.generated = datetime_literal()
        self.posit = posit_uri
        self.asserts = asserts

    def to_triples(self):
        subj = self.uri
        if self.asserts is None:
            triples = [ (subj, RDF.type, self.type),
                        (subj, RDFS.label, self.label),
                        (subj, URIRef(disco.Posits.iri), URIRef(self.posit)),
                        (subj, URIRef(disco.GeneratedOn.iri), self.generated)
                        ]
        elif self.asserts == True:
            triples = [ (subj, RDF.type, self.type),
                        (subj, RDFS.label, self.label),
                        (subj, URIRef(disco.Asserts.iri), URIRef(self.posit)),
                        (subj, URIRef(disco.GeneratedOn.iri), self.generated)
                        ]
        elif self.asserts == False:
            triples = [ (subj, RDF.type, self.type),
                        (subj, RDFS.label, self.label),
                        (subj, URIRef(disco.Refutes.iri), URIRef(self.posit)),
                        (subj, URIRef(disco.GeneratedOn.iri), self.generated)
                        ]
        else:
            # Not true, not false, not None - what is it?
            assert False
        return triples

class Discourse(object):

    def unpack_payload(self, payload):
        payload_m=set()
        for k,v in payload.items() :
            payload_m.add ((self.uri, k , v))
        return payload_m
    # Payload is the additional metadata provided by the author that can be used to index the discourse
    def __init__(self, name, payload=None):
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace+"#")
        self.type = URIRef(disco.Discourse.iri)
        self.label = Literal(f"discourse_{name}")
        self.generated = datetime_literal()
        self.members = set()
        self.exclusions = set()
        if payload is None:
            payload={}
        self.payload = self.unpack_payload(payload)
        self.member_assertions = { None : set(),
                           True : set(),
                           False : set()}
        self.member_exclusions = { None : set(),
                           True : set(),
                           False : set()}
        # Not strictly a posit, but named as such to align the DiscourseContains
        # membership api to allow Discourses to reference one another.
        self.posit = self.uri

    def add_member(self, member, assertion=None):
        
        if isinstance(member, rdflib.URIRef):

            self.members.add(member)
            self.member_assertions[assertion].add(member)
        elif isinstance(member, Declaration):
            self.members.add(member.uri)
            self.member_assertions[assertion].add(member.posit)

    def add_exclusion(self, exclusion_member, assertion=None):
        self.exclusions.add(exclusion_member.uri)
        self.member_exclusions[assertion].add(exclusion_member.posit)

    def clear_members(self):
        self.members=set()
        self.member_assertions={ None : set(),
                                True : set(),
                                False : set()}
        print("Cleared Members")
        print("Member Count:", len(self.members))


    def member_hash(self):
        hash_object = []
        key_set = [None, True, False]
        for k in key_set:
            k_list = sorted(list(self.member_assertions[k]))
            hash_object.append(k_list)
        return uuid_format(hashlib.md5(bytes(str(hash_object),encoding="utf-8")).hexdigest())


    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, URIRef(disco.GeneratedOn.iri), self.generated),
                    (subj, URIRef(disco.DiscourseHash.iri), Literal(self.member_hash())),
                    ]
        print("self.members:", len(self.members))
        for m in self.members:
            triples.append((subj, URIRef(disco.DiscourseContains.iri), m))

        for m in self.exclusions:
            triples.append((subj, URIRef(disco.DiscourseExcludes.iri), m))

        for t in self.payload:
            triples.append(t)

        return triples
