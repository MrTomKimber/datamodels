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


def datetime_literal(dt=None):
    if dt is None:
        dt_s = datetime.now(timezone.utc).strftime("%Y-%M-%dT%H:%M:%S")
    else:
        dt_s = dt.strftime("%Y-%M-%dT%H:%M:%S")
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

onto = owlr.get_ontology("discourse.owl").load()
namespace = onto.base_iri

class Posit(object):
    def __init__(self, triple):
        s,p,o = triple
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace+"#")
        self.type = URIRef(onto.Posit.iri)
        self.label = Literal(f"posit_{uid}")
        self.longform = Literal(triple_to_longform(triple))
        self.subject = s
        self.predicate = p
        self.object = o

    # Where a Posit turns out to already exist in the graph,
    # use this method to edit the uri of this representation
    # to align it to the graph
    def update_uri_from_graph(self, graph):
        search = list(graph.triples((None,URIRef(onto.Digest.iri), self.longform)))
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
        if len (list(graph.triples((None,URIRef(onto.Digest.iri), self.longform))))>0:
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
                    (subj, URIRef(onto.Subject.iri), self.subject),
                    (subj, URIRef(onto.Predicate.iri), self.predicate),
                    (subj, URIRef(onto.Object.iri), self.object),
                    (subj, URIRef(onto.Digest.iri), self.longform)
                    ]
        return triples


class Declaration(object):
    def __init__(self, posit_uri):
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace+"#")
        self.type = URIRef(onto.Declaration.iri)
        self.label = Literal(f"declaration_{uid}")
        self.generated = datetime_literal()
        self.posit = posit_uri

    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, URIRef(onto.Posits.iri), URIRef(self.posit)),
                    (subj, URIRef(onto.GeneratedOn.iri), self.generated)
                    ]
        return triples

class Discourse(object):
    def __init__(self, name, is_proposed_by = None):
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace+"#")
        self.type = URIRef(onto.Discourse.iri)
        self.label = Literal(f"discourse_{name}")
        self.generated = datetime_literal()
        self.members = []
        self.is_proposed_by = is_proposed_by

    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, URIRef(onto.GeneratedOn.iri), self.generated)
                    ]
        for m in self.members:
            triples.append((subj, URIRef(onto.DiscourseContains.iri), m))

        if self.is_proposed_by:
            #print(self.is_proposed_by)
            triples.append((subj, URIRef(onto.isProposedBy.iri), self.is_proposed_by))
            # Inverse property written here, since this side is the many in the many-to-one
            triples.append((self.is_proposed_by, URIRef(onto.Proposes.iri), subj))
            # And now for the transitive fact that any members of this discourse are also proposeby the same thing:
            for m in self.members:
                triples.append((m, URIRef(onto.isProposedBy.iri), self.is_proposed_by))
                triples.append((self.is_proposed_by, URIRef(onto.Proposes.iri), m))
        return triples
