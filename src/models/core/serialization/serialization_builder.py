
import jsonschema
import json

import owlready2 as owlr

import xml.etree.ElementTree as ET
import uuid
import re
from rdflib import URIRef
from itertools import chain
import os


ser_file = "Serialization.owl"
MODPATH=os.path.split(__file__)[0]
serial = owlr.get_ontology(os.path.join(MODPATH,ser_file)).load()
serialization_schema_filename = os.path.join(MODPATH, "serialisation_schema.json")

def process_json_serialization(jsonfilename):
    """Given a filename pointing to a json data file, read it and convert into a formatted XML/RDF file containing the Serialization specifications for appliction in a load-process. """
    # Identify/Validate that the file exists, and is in the right format:
    if validate_schema(jsonfilename, serialization_schema_filename):
        with open(jsonfilename, 'r') as file:
            data = json.load(file)

        r = process_serialisation_to_elementtree(data)
        #return r
        ET.indent(r, space="\t", level=0)

        print(r)

        comment = """<!--
        Sample Schema Name
        -->\n"""
        xml_text = """<?xml version='1.0' encoding='utf-8'?>\n""" + comment + ET.tostring(r).decode()
        return xml_text

    else:
        assert False
# TODO: Create a simple template from a serialisation expression file
def gen_serialisation_template(jsonfilename):
    with open(jsonfilename, 'r') as file:
        jdata = json.load(file)
    mapping_value_list = fetch_mapping_values(jdata)
    return mapping_value_list

def validate_schema(datafilename, schemafilename):
    """Given a datafile, and associated json schema filename, perform commodity level validation check"""
    with open(schemafilename, 'r') as file:
        schema = json.load(file)
    
    with open(datafilename, 'r') as file:
        data = json.load(file)

    
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.ValidationError as e:
        raise e


def process_serialisation_to_elementtree(jdata):
    """Given the data provided from a validated file, proceed to convert from the json data into elementtree format for 
    a number of separate blocks of information
    1) Serialization Top Level
    2) Mapping Level
    3) Meta Targets
    4) Translation Mappings
    5) KVPair Elements
    6) Serialization Ontology Objects (Classes)
    7) Serialization Ontology Objects (Properties and Data Properties)
    """

        
    ns_map = [('xmlns',"http://www.w3.org/2002/07/owl#"),
              ('xml:base',"http://www.w3.org/2002/07/owl"),
              ('xmlns:rdf',"http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
              ('xmlns:owl',"http://www.w3.org/2002/07/owl#"),
              ('xmlns:dc',"http://purl.org/dc/elements/1.1/"),
              ('xmlns:rdfs',"http://www.w3.org/2000/01/rdf-schema#"), 
              ('xmlns:ser', serial.base_iri)
             ]
    
    serialization_iri = jdata["serialization_iri"]

    # A list of extracted mapping value details, extracted for use in preparing a number of sub-blocks in addition to itself
    mapping_value_list = fetch_mapping_values(jdata)
    translation_mappings = [(k,v) for k,v in jdata.get("translation_mappings", {}).items()]
    print(translation_mappings)

    ## Collect a list of appendable elements to be included in the final RDF file
    ## *************************************************************************** ##
    ## *************************************************************************** ##
    serialization_classes = gen_serialization_classes()
    annotation_properties = gen_annotation_properties()
    meta_targets = gen_meta_targets(jdata)
    mapping_headers = gen_mappings(mapping_value_list, jdata)
    if len(translation_mappings)>0:
        translation_mapping_headers=gen_translation_mappings(jdata, translation_mappings)
    else:
        translation_mapping_headers=[]
    serialization_definition = gen_serialization_def(mapping_value_list,jdata)


    combined_definitions = list(chain(*[serialization_definition, serialization_classes, annotation_properties, meta_targets, mapping_headers, translation_mapping_headers]))
    ## End of collection functions.
    ## *************************************************************************** ##
    ## *************************************************************************** ##


    X = ET.Element('rdf:RDF')
    default_namespace='http://www.company.com'
    for prefix, uri  in ns_map:
        X.set(prefix, uri)
    
    
    print(combined_definitions)
    for element in combined_definitions:
        #e = ET.SubElement(X, element)
        X.append(element)
    return X



def gen_serialization_classes():
    X = []
    c = ET.Comment("""///////////////////////////////////////////////////////////////////////////////////////
    //
    // Serialization Classes - these should remain static
    // High level serialization classes defined to describe a given Serialization
    //
    ///////////////////////////////////////////////////////////////////////////////////////""") 
    X.append(c)
    ## Add block for serialization objects:
    for iri in [serial.Serialization.iri, 
              serial.Mapping.iri,
              serial.MetaClass.iri,             
              serial.MetaProperty.iri,
              serial.MetaDataProperty.iri, 
              serial.MetaStaticProperty.iri, 
              serial.TranslationMapping.iri, 
              serial.MappingKVPair.iri
              ]:
        q = ET.Element("Class")
        q.set("rdf:about", iri)
        X.append(q)
    return X


def gen_annotation_properties():
    X = []
    comment = """///////////////////////////////////////////////////////////////////////////////////////
    //
    // Annotation properties - these should remain static
    // These are the internal technical components used by the loading/serialization process
    // that map onto the Serialization Ontology's Data Properties
    //
    ///////////////////////////////////////////////////////////////////////////////////////"""
    c = ET.Comment(comment)
    X.append(c)
    
    for iri in [ serial.ContainsMapping.iri,               
                 serial.MappingMetaTarget.iri,
                 serial.MappingDomain.iri,
                 serial.MappingRange.iri,
                 serial.MappingMetaTarget.iri,
                 serial.SerializationLabel.iri,
                 serial.SerializationParentLabel.iri, 
                 serial.Key.iri, 
                 serial.Value.iri,
                 serial.TranslationMappingName.iri ]:
        q = ET.Element("AnnotationProperty")
        q.set("rdf:about", iri)
        X.append(q)
    return X

def gen_meta_targets(jdata):
    X = []

    serialization_iri = jdata["serialization_iri"]

    comment = """
    
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Individuals - here define all the final target classes and properties 
    // (Using the MetaClass, MetaProperty and MetaDataProperty that will be 
    // referenced by the serialization and populated by individual Mapping elements
    // using the MappingMetaTarget pointer. ) 
    // For any given ontology (or ontologies) this collection identifies and names key
    // Classes, Properties and Data Properties that the Serialization function will populate. 
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     """
    c = ET.Comment(comment)
    X.append(c)
    meta_defs = []
    cls_uri_decodes={
        "targetClasses" : "http://www.tkltd.org/ontologies/serialization#MetaClass",
        "targetProperties" : "http://www.tkltd.org/ontologies/serialization#MetaProperty", 
        "targetDataProperties" : "http://www.tkltd.org/ontologies/serialization#MetaDataProperty", 
        "targetStaticProperties" : "http://www.tkltd.org/ontologies/serialization#MetaStaticProperty"
    }

    for cls in ["targetClasses","targetProperties", "targetDataProperties", "targetStaticProperties"]:
        cls_defs = jdata.get(cls)
        for c in cls_defs:
            meta_defs.append((c, cls_uri_decodes[cls]))

    for iri,tp in meta_defs:
        p = ET.Element("NamedIndividual")
        p.set("rdf:about", iri)
        q = ET.SubElement(p, "rdf:type")
        q.set("rdf:resource", tp)
        r = ET.SubElement(p, "ser:IsComponentOfSerialization")
        r.set("rdf:resource", serialization_iri)
        X.append(p)

    return X


def find_match(value, match_set_list):
    for e,t_set in enumerate(match_set_list):
        if value in t_set:
            return e
    return None

def fetch_mapping_values(jdata):
    mapping_list = []
    t_classes, t_properties, t_data_properties = jdata['targetClasses'], jdata['targetProperties'], jdata['targetDataProperties']
    t_static_properties = jdata.get('targetStaticProperties', [])
    uri_base = jdata['serialization_iri'][:jdata['serialization_iri'].find("#")]+"#"
    for mapping in jdata['serialization_mappings']:
        t_match=find_match(mapping['target'],[t_classes, t_properties, t_data_properties, t_static_properties])
        
        mapping_name = "".join([uri_base, mapping['mapping_name']])
        match t_match:
            case 0:
                # Classes
                properties = {k:v for k,v in {"ser:SerializationLabel" : mapping.get("label"),
                            "ser:SerializationParentLabel" : mapping.get("parent_label")}.items() if v is not None}
                
                mapping_list.append((mapping_name, mapping['target'], t_match, properties))
            case 1:
                # Properties
                properties = {k:v for k,v in {"ser:MappingDomain" : mapping.get("domain"),
                            "ser:MappingRange" : mapping.get("range")}.items() if v is not None}
                mapping_list.append((mapping_name,mapping['target'], t_match, properties))
                
            case 2:
                # Data Properties
                properties = {k:v for k,v in {"ser:MappingDomain" : mapping.get("domain"),
                            "ser:MappingRange" : mapping.get("range")}.items() if v is not None}
                mapping_list.append((mapping_name,mapping['target'], t_match, properties))
            case 3:
                # Static Properties
                properties = {k:v for k,v in {"ser:MappingDomain" : mapping.get("domain"),
                            "ser:MappingRange" : mapping.get("range"),
                            "ser:TranslationMappingName" : mapping.get("translation_mapping_name")}.items() if v is not None}
                mapping_list.append((mapping_name, mapping['target'], t_match, properties))
                
            case None:
                # No Match
                print("**********************************************")
                print("**                                          **")
                print("**         This mapping not matched         **")
                print("**                                          **")
                print("**********************************************")
                print(mapping)
                print("**********************************************")
                print()
                print()
                assert False
    return mapping_list

def gen_mapping_element(mapping_tuple, jdata):
    name, target, ttype, properties = mapping_tuple
    serialization_iri = jdata["serialization_iri"]
    X = ET.Element("NamedIndividual")
    X.set("rdf:about", name)
    q = ET.SubElement(X,"rdf:type")
    q.set("rdf:resource", serial.Mapping.iri)
    q = ET.SubElement(X,"ser:MappingMetaTarget")
    q.set("rdf:resource", target)
    q = ET.SubElement(X, "ser:IsComponentOfSerialization")
    q.set("rdf:resource", serialization_iri)
    
    for k,v in properties.items():
        q = ET.SubElement(X,k)
        q.text =str(v)
    return X

def gen_mappings(mapping_list, jdata):
    element_list = []
    comment = """
    
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Mappings - define all the Mappings that will be collated by this serialisation to
    // pull content from the `flat` recordset and assign it to classes, properties or 
    // data properties as defined in the overarching ontology. 
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     """
    c = ET.Comment(comment)
    element_list.append(c)
    for mapping in mapping_list:
        element_list.append(gen_mapping_element(mapping, jdata))
    return element_list



def gen_translation_mappings(jdata, translation_mappings_list):
    serialization_iri = jdata["serialization_iri"]
    manifest={}
    elements = []
    comment = """   
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Translation Mappings - optional static decode tables used to translate from input
    // values found in the serialization to target values expected by the ontology.
    //
    ///////////////////////////////////////////////////////////////////////////////////////"""
    c = ET.Comment(comment)
    elements.append(c)

    for list_item in translation_mappings_list:
        print(list_item)
        name, d = list_item
        tm_id = serialization_iri + uuid.uuid4().hex
        tm_type = serial.TranslationMapping.iri
        tm_label = name
        manifest[name]={"id": tm_id, "type" : tm_type, "label" : tm_label, "kvpairs" : [] }
        for k,v in d.items():
            kv_id = serialization_iri + uuid.uuid4().hex
            kv_type = serial.MappingKVPair.iri
            manifest[name]['kvpairs'].append((kv_id, kv_type, k, v))
        print("////////////////////")
        print(manifest[name])
        print("////////////////////")
        d = manifest[name]
        X = ET.Element("NamedIndividual")
        X.set("rdf:about", d['id'])
        q = ET.SubElement(X,"rdf:type")
        q.set("rdf:resource", d['type'])    
        q = ET.SubElement(X,"rdfs:label")
        q.text=name    
        q = ET.SubElement(X,"ser:IsComponentOfSerialization")
        q.set("rdf:resource", serialization_iri)    
        
        for kv_id, kv_type, k,v in d['kvpairs']:
            q = ET.SubElement(X,"ser:ContainsTranslationMappingKVPair")
            q.set("rdf:resource", kv_id)
        
        elements.append(X)


    c = ET.Comment("""///////////////////////////////////////////////////////////////////////////////////////
    //
    // KVP sub elements associated with the above Translation Mappings
    //
    ///////////////////////////////////////////////////////////////////////////////////////""") 
    elements.append(c)

    for name, d in manifest.items():
        for kv_id, kv_type, k, v in d['kvpairs']:
            kvp_elem = ET.Element("NamedIndividual")    
            kvp_elem.set("rdf:about", kv_id)
            q = ET.SubElement(kvp_elem,"ser:IsComponentOfSerialization")
            q.set("rdf:resource", serialization_iri)    
            q = ET.SubElement(kvp_elem, "rdf:type")
            q.set("rdf:resource", kv_type)
            q = ET.SubElement(kvp_elem,"ser:Key")
            q.text = k
            q = ET.SubElement(kvp_elem,"ser:Value")
            q.text = v
            elements.append(kvp_elem)


    return elements

def gen_serialization_def(mapping_value_list, jdata):
    elements = []

    serialization_iri = jdata['serialization_iri']


    comment = """   
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Serialization - define the named Serialization Object and assign the set of 
    // mappings that belong to that object.
    //
    ///////////////////////////////////////////////////////////////////////////////////////"""
    c = ET.Comment(comment)
    elements.append(c)

    X = ET.Element("NamedIndividual")
    X.set("rdf:about", serialization_iri)
    q = ET.SubElement(X,"rdf:type")
    q.set("rdf:resource", serial.Serialization.iri)
    q = ET.SubElement(X,"ser:IsComponentOfSerialization")
    q.set("rdf:resource", serialization_iri)    
    for m in mapping_value_list:
        q = ET.SubElement(X,"ser:ContainsMapping")
        q.set("rdf:resource", m[0])
        
    q = ET.SubElement(X,"rdfs:label")
    q.text=jdata['serialization_label']
    elements.append(X)
    return elements

