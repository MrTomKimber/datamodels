


import rdflib
from rdflib import URIRef, Literal, Graph, Namespace
from rdflib.namespace import RDF, RDFS

from datetime import datetime, timezone
import uuid
from itertools import chain

import owlready2 as owlr

# This file is coupled with Serialization.owl, an ontology that defines
# the specification for translating between row-based content and graph-content.

serial_onto_file = "Serialization.owl"
try:
    serial = owlr.get_ontology(serial_onto_file).load()
except FileNotFoundError:
    serial = owlr.get_ontology("../" + serial_onto_file).load()

namespace = serial.base_iri

def flush(onto):
    for m in onto.classes():
        print(m, m.is_a)
flush(serial)
owlr.sync_reasoner(serial)


def get_lineage(d, l, acc=None):
    if acc is None:
        if l is not None:
            acc=[l]
    q = d.get(l)
    if q is not None:
        acc.append(q)
        acc = get_lineage(d, q, acc)
    return acc



# Assume the convention that data is passed by dictionary
# with key-value pairs containing data attributes
def first(non_consuming_iterable):
    for n in non_consuming_iterable:
        return n

def ontology_definitions():
    return {
            "Mapping_uri" : URIRef(serial.Mapping.iri),
            "Serialization_uri" : URIRef(serial.Serialization.iri),
            "IsSerializationComponent_uri" : URIRef(serial.IsComponentOfSerialization.iri),
            "MappingMetaTarget_uri" : URIRef(serial.MappingMetaTarget.iri),
            "MetaClass_uri" : URIRef(serial.MetaClass.iri),
            "MetaProperty_uri" : URIRef(serial.MetaProperty.iri),
            "MetaDataProperty_uri" : URIRef(serial.MetaDataProperty.iri),
            "MetaStaticProperty_uri" : URIRef(serial.MetaStaticProperty.iri),
            "MappingDomain_uri" : URIRef(serial.MappingDomain.iri),
            "MappingRange_uri" : URIRef(serial.MappingRange.iri),
            "SerializationLabel_uri" : URIRef(serial.SerializationLabel.iri),
            "SerializationParentLabel_uri" : URIRef(serial.SerializationParentLabel.iri),
            "TranslationMappingName_uri" : URIRef(serial.TranslationMappingName.iri),
            "TranslationMapping_uri" : URIRef(serial.TranslationMapping.iri),
            "MappingKVPair" : URIRef(serial.MappingKVPair.iri),
            "ContainsMapping_uri" : URIRef(serial.ContainsMapping.iri),
            "ContainsTranslationMapping_uri" : URIRef(serial.ContainsTranslationMapping.iri),
            "ContainsTranslationMappingKVPair_uri" : URIRef(serial.ContainsTranslationMappingKVPair.iri),
            "Key_uri" : URIRef(serial.Key.iri),
            "Value_uri" : URIRef(serial.Value.iri),
            "ContainsTranslationMappingKVPair_uri" : URIRef(serial.ContainsTranslationMappingKVPair.iri),
            "UniqueIdentifier_uri" : URIRef(serial.UniqueIdentifier.iri)
    }



class Entity(object):

    def __init__(self, e_type, label, unique_label=None, entity_map=None):
        if unique_label is None:
            unique_label=label
        uid = uuid.uuid4().hex
        self.uri = URIRef(uid, namespace)
        self.name = label
        self.type = e_type
        self.label = Literal(label)
        self.unique_label = Literal(unique_label)
        if entity_map is None:
            entity_map = { self.unique_label : self.uri }

        if self.unique_label in entity_map.keys():
            self.uri = entity_map[self.unique_label]
        elif self.unique_label not in entity_map.keys():
            entity_map[self.unique_label]=self.uri

        self.data_properties=[]
        self.properties=[]

    def to_triples(self):
        subj = self.uri
        triples = [ (subj, RDF.type, self.type),
                    (subj, RDFS.label, self.label),
                    (subj, ontology_definitions()["UniqueIdentifier_uri"], self.unique_label),
                    ]
        for p in self.data_properties:
            triples.append((subj, p[1], p[2]))
        for p in self.properties:
            triples.append((subj, p[1], p[2]))
        return triples


class Mapping(object):
    @staticmethod
    def unbind_ns_strings(value, ns_list):
        for nsc,nsf in ns_list:
            if value.replace(nsc+":", nsf) != value:
                return value.replace(nsc+":", nsf)
        return value
    
    def __repr__(self):
        return "<" + ">" + str(dict((name, value) for name, value in self.__dict__.items() if not name.startswith('__')))
    
    def __init__(self, parent_serialization, s_uri):
        self.ontology = serial
        self.serialization = parent_serialization
        self.graph = parent_serialization.graph

        serns = Namespace(serial.base_iri)
        ns_list = [('ser', serns)]

        self.defs = ontology_definitions()
        self.name = s_uri.split("#")[-1]
        # Class Pointer
        mapping_meta_target = first([o for s,p,o in self.graph.triples((URIRef(s_uri), self.defs["MappingMetaTarget_uri"], None)) ])
        self.mapping_meta_target = mapping_meta_target
        
        class_set = set([URIRef(Mapping.unbind_ns_strings(t, ns_list)) for r,s,t in self.graph.triples((mapping_meta_target, RDF.type, None)) ])


        if self.defs["MetaClass_uri"] in class_set:
            self.mapping_subtype = "class"
        elif self.defs["MetaProperty_uri"] in class_set:
            self.mapping_subtype = "property"
        elif self.defs["MetaDataProperty_uri"] in class_set:
            print(class_set)
            print("dataproperty")
            print(self.name)
            self.mapping_subtype = "dataproperty"
        elif self.defs["MetaStaticProperty_uri"] in class_set:
            self.mapping_subtype = "staticproperty"
        else:
            print( "meta_target", mapping_meta_target )
            print ("class_set", class_set)
            print ( "mc_uri", self.defs["MetaClass_uri"])
            print(self.defs["MetaClass_uri"] in class_set)
            print(type(self.defs["MetaClass_uri"]), [type(n) for n in class_set])
            print( "uri", s_uri )
            self.mapping_subtype = "unexpected_thing"
            print()
            assert False
        print( self.name, "is a ", self.mapping_subtype)
        # Create a mapping_properties dictionary to hold the extracted mapping details
        # SerializationLabel --> Data Header
        # SerializationParentLabel --> Used to construct "lineage tree"
        # MappingDomain --> For properties, acts as a pointer to the subject class/item
        # MappingRange --> For  properties acts as a pointer to the object class/item

        mapping_properties = {p:o for q in [self.defs["MappingDomain_uri"],
                                            self.defs["MappingRange_uri"],
                                            self.defs["TranslationMappingName_uri"],
                                            self.defs["SerializationLabel_uri"],
                                            self.defs["SerializationParentLabel_uri"]] \
                                  for s,p,o in self.graph.triples((URIRef(s_uri), q, None))}

        mapping_properties = {q[0]:o for q in [(n,self.defs[n]) for n in
                                            ["MappingDomain_uri",
                                            "MappingRange_uri",
                                            "TranslationMappingName_uri",
                                            "SerializationLabel_uri",
                                            "SerializationParentLabel_uri"]] \
                                  for s,p,o in self.graph.triples((URIRef(s_uri), q[1], None))}

        for p,v in mapping_properties.items():
            setattr(self, p.replace("_uri",""),v.toPython())

        #print (" -----------------------")
        #print(s_uri, self.mapping_subtype, mapping_properties)
        #print (" -----------------------")
        # All these mapping data-properties should be packaged into some
        # utility data-object for traversal/configuration at load-time.

    def _apply_mapping(self, row_dict, row_entity_context, entity_mappings=None):

        if self.mapping_subtype=="class" and hasattr(self, "SerializationLabel"):
            label = row_dict.get(self.SerializationLabel)
            lineage = get_lineage(self.serialization.lineage_tree, self.SerializationLabel)
            unique_label = ".".join([row_dict.get(l) if row_dict.get(l) is not None else "_" for l in lineage][::-1])

            return Entity(self.mapping_meta_target, label, unique_label, entity_mappings)

        else:
            subj = row_entity_context.get(self.MappingDomain)
            prop = URIRef(self.mapping_meta_target)
            if subj is not None:
                if self.mapping_subtype=="property":
                    obj = row_entity_context.get(self.MappingRange)
                    print(self.MappingRange, "processing property", prop, obj)
                    if obj is not None:
                        subj.properties.append((subj.name, prop, URIRef(obj.uri)))
                    else:
                        print(row_entity_context)
                        for k,v in row_entity_context.items():
                            print(k,v.name)
                        pass
                elif self.mapping_subtype=="dataproperty":
                    obj = row_dict.get(self.MappingRange)
                    if obj is not None:
                        subj.data_properties.append((subj.name, prop, Literal(obj)))
                elif self.mapping_subtype=='staticproperty':
                    # This is where the dereferencing of staticproperties goes.
                    print("/////STATICPROPERTY/////")
                    print( subj, prop)
                    print ("********")
                    try:    
                        print( self.TranslationMapping )
                    except:
                        print (dir (self))
                    print ("********")
                    print( row_entity_context , row_dict, self.TranslationMappingName )
                    
                    mapping_name = self.TranslationMappingName
                    print("/////////\\\\\\\\\\")
                    print(self.serialization.translation_mappings)
                    print("/////////\\\\\\\\\\")
                    print (mapping_name, self.serialization.translation_mappings.get(mapping_name))
                    print()
                    print(mapping_name, self.MappingRange)
                    print(row_dict)
                    obj = self.serialization.translation_mappings.get(mapping_name,{}).get(row_dict.get(self.MappingRange), None)
                    if obj is not None:
                        subj.properties.append((subj.name, prop, obj))
                    else:
                        assert False # Returned an obj of None
                return subj
            else:
                # No matching subject -
                return None




# A serialization spec is a data structure used to convert serial (row-based) data
# into a graph (and maybe back again? tbd)
# The spec will normally be written in rdf, and passed as an rdflib graph.
# This graph is decomposed into a dict-like object, for convenience

class Serialization(object):

    def __init__(self, s_graph, s_name):
        self.ontology = serial
        self.graph = s_graph

        self.defs = ontology_definitions()

        serial_dict = self.return_serialization_labels()
        if s_name in serial_dict:
            self.serialization = serial_dict.get(s_name)
        else:
            print(serial_dict)
            print(s_graph, s_name)
            assert False # Serialization name should match up

        self.mappings = self.get_mappings()

        self.lineage_tree = {m.SerializationLabel: m.SerializationParentLabel for m in self.mappings if m.mapping_subtype=="class" and hasattr(m, "SerializationParentLabel")}
        self.meta_classes, self.meta_properties, self.meta_data_properties, self.meta_static_properties = self.get_meta_targets()
        self.meta_objects = [v for m in [self.meta_classes, self.meta_properties, self.meta_data_properties, self.meta_static_properties] for v in m]
        
        self.translation_mappings = self.get_translation_mappings()


        # Capture dereferencing Translation Mapping sets
        print("****************************************")
        print(self.graph)
        print("This is the Serialization __init__ method")
        print(s_graph, s_name)
        print(type(s_graph))
        print(self.meta_classes, self.meta_properties, self.meta_data_properties, self.meta_static_properties)
        print("****************************************")
        #translation_mappings



    def get_meta_targets(self):
        meta_classes = [s.toPython() for s,p,m in self.graph.triples((None,
                                                                        RDF.type,
                                                                        ontology_definitions().get("MetaClass_uri")))]
        meta_properties = [s.toPython() for s,p,m in self.graph.triples((None,
                                                                                RDF.type,
                                                                                ontology_definitions().get("MetaProperty_uri")))]
        meta_data_properties = [s.toPython() for s,p,m in self.graph.triples((None,
                                                                                RDF.type,
                                                                                ontology_definitions().get("MetaDataProperty_uri")))]
        meta_static_properties = [s.toPython() for s,p,m in self.graph.triples((None,
                                                                                RDF.type,
                                                                                ontology_definitions().get("MetaStaticProperty_uri")))]
        
        return meta_classes, meta_properties, meta_data_properties, meta_static_properties


    def return_serialization_labels(self):
        """Return a dictionary of Serialization objects, keyed by label"""
        # Makes use of serial.Serialization
        serialization_instances = [a for a,b,c in self.graph.triples((None,RDF.type,self.defs["Serialization_uri"]))]
        serial_instance_dict_by_label = { l.value : s.toPython() for i in serialization_instances for s,p,l in self.graph.triples((i, RDFS.label, None))}
        return serial_instance_dict_by_label

    def get_translation_mappings(self):
        self.translation_mappings = {}
        trans_mappings = {}
        
        serns = Namespace(serial.base_iri)
        self.graph.bind('ser', serns, override=True, replace=True)
        translation_mapping_ids = [s.toPython() for s,p,m in self.graph.triples((None,
                                                                        RDF.type,
                                                                        URIRef(serial.TranslationMapping.iri)))]
        
        print("translation_mapping_ids", translation_mapping_ids)
        for tmid in translation_mapping_ids:
            print(tmid)
            tmk_def={}
            tmk_ids = [o.toPython() for s,p,o in self.graph.triples((URIRef(tmid),
                                                                    URIRef(serial.ContainsTranslationMappingKVPair.iri),
                                                                    None))]
            
            tm_names = {s.toPython():o.toPython() for s,p,o in self.graph.triples((URIRef(tmid),
                                                                    RDFS.label,
                                                                    None))}
            for tmk_id in tmk_ids:
                k = [o.toPython() for s,p,o in self.graph.triples((URIRef(tmk_id),
                                                                    URIRef(serial.Key.iri),
                                                                    None))]
                v = [o.toPython() for s,p,o in self.graph.triples((URIRef(tmk_id),
                                                                    URIRef(serial.Value.iri),
                                                                    None))]
                if len(k)==1 and len(v)==1:
                    k,v=k[0], v[0]
                else:
                    print(k,v)
                    assert False # Length of k,v lists is not == 1
                if v in self.meta_objects:
                    # This means the values are canonical uris for this serialization, convert them from text.
                    v = URIRef(v)
                else:
                    v = str(v)
                tmk_def[k]=v
            trans_mappings[tm_names[tmid]]=tmk_def

        return trans_mappings

    
        

        
        

    def get_mappings(self):
        self.mappings=[]

        mapping_idents = [m.toPython() for s,p,m in self.graph.triples((URIRef(self.serialization),
                                                                        self.defs["ContainsMapping_uri"],
                                                                        None))]
        # Mapping Idents are the entities to which all the other properties are  associated
        for m in mapping_idents:
            self.mappings.append(Mapping(self, m))

        return self.mappings

    def delta_triples_to_target_graph(self, row_set, target_graph, deltas=False, in_place=False):
        if not in_place:
            temp_graph=Graph()
            serns = Namespace(serial.base_iri)
            temp_graph.bind('ser', serns, override=True, replace=True)
            for t in target_graph.triples((None, None, None)):
                temp_graph.add(t)
        else:
            temp_graph=target_graph
        mastered_triples=[]
        for row in row_set:
            t = self.extract_raw_triples(row)
            if deltas:
                triples = set(self.master_triples(temp_graph, t)).difference(set(temp_graph.triples((None, None, None))))
            else:
                triples = set(self.master_triples(temp_graph, t))
            for m in triples:
                temp_graph.add(m)
                mastered_triples.append(m)
        return mastered_triples




    def extract_raw_triples(self, row, entity_mappings=None):
        entities={}
        if entity_mappings is None:
            entity_mappings={}
        for m in self.mappings:
            
            if hasattr(m, "SerializationLabel"):
                
                if row.get(m.SerializationLabel) is not None:
                    ent=m._apply_mapping(row, None, entity_mappings)
                    entities[m.SerializationLabel]=ent
                    entity_mappings[ent.unique_label]=ent.uri
            
            else:
                print(m, " has no SerializationLabel!!")
        print([(k) for k,v in entity_mappings.items()])

        for m in self.mappings:

            if not hasattr(m, "SerializationLabel"):
                print(m.name)
                m._apply_mapping(row, entities, entity_mappings)
            else:
                print(m, " has no SerializationLabel!!")

        return list(chain (*[e.to_triples() for e in entities.values()])), entity_mappings

    # Given a graph that already exists, and a set of new triples for mastering,
    # update that triple-set so that they use the equivalent mastered object-identifiers.

    # This process means finding any matching UniqueIdentifiers for same-class objects
    # or across all object types - (see "strict_by_type" option)
    # Re-attributing objects in the process.

    def master_triples(self, master_graph, triples, strict_by_type=False):

        # "ser" namespace must be defined in both the master_graph,
        # and the new graph used to temporarily host the proposed set of triples.
        input_graph = Graph()
#        input_graph.parse (serial_onto_file, format='xml')
        serns = Namespace(serial.base_iri)
        input_graph.bind('ser', serns, override=True, replace=True)
        master_graph.bind('ser', serns, override=True, replace=True)

        for t in triples:
            input_graph.add(t)

        if strict_by_type: # In this branch, keys are only accepted where unique id and class type is a match
            subj_unique_q = """SELECT distinct ?s ?t ?u
                                WHERE {
                                ?s ser:UniqueIdentifier ?u .
                                OPTIONAL {?s a ?t.}
                                } """

            master_keys = dict([((t,u),s) for s,t,u in list(master_graph.query(subj_unique_q))])
            input_keys = dict([((t,u),s) for s,t,u in list(input_graph.query(subj_unique_q))])

        else: # while here, is the looser logic where uniqueid must apply irrespective of type
            subj_unique_q = """SELECT distinct ?s ?u
                                WHERE {
                                ?s ser:UniqueIdentifier ?u .
                                } """
            master_keys = dict([(u,s) for s,u in list(master_graph.query(subj_unique_q))])
            input_keys = dict([(u,s) for s,u in list(input_graph.query(subj_unique_q))])

        switch_dict = {v:master_keys.get(k,v) for k,v in input_keys.items()}

        new_triples = []
        for s,p,o in triples:
            if not(s,p,o) in master_graph:
                new_triples.append((switch_dict.get(s,s), switch_dict.get(p,p), switch_dict.get(o,o)))

        return new_triples







def row_to_graph(data_row, serialization_spec):
    pass
