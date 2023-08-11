
import jsonschema
import json

import owlready2 as owlr

import xml.etree.ElementTree as ET
import uuid
import re

sample_ser_file = "../Serialization.owl"
serial = owlr.get_ontology(sample_ser_file).load()


def process_json_serialization(schemafilename):
    # Identify/Validate that the file exists, and is in the right format:
    if validate_serialization_schema(schemafilename):
        with open(schemafilename, 'r') as file:
            data = json.load(file)

        r = process_serialisation(data)

        ET.indent(r, space="\t", level=0)

        print(r)

        comment = """<!--
        Sample Schema Name
        -->\n"""
        xml_text = """<?xml version='1.0' encoding='utf-8'?>\n""" + comment + ET.tostring(r).decode()
        return xml_text

    else:
        assert False



def validate_serialization_schema(schemafilename):
    with open('/home/tomk/Documents/Coding/gitHub/datamodels/serialisation_schema.json', 'r') as file:
        schema = json.load(file)
    
    with open(schemafilename, 'r') as file:
        data = json.load(file)

    
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.ValidationError as e:
        raise e




def create_mapping(name, target, ttype, properties={}):
    X = ET.Element("NamedIndividual")
    X.set("rdf:about", name)
    q = ET.SubElement(X,"rdf:type")
    q.set("rdf:resource", serial.Mapping.iri)
    q = ET.SubElement(X,"ser:MappingMetaTarget")
    q.set("rdf:resource", target)
    
    for k,v in properties.items():
        q = ET.SubElement(X,k)
        q.text =str(v)
    return X

def generate_meta_definitions(onto):
    meta_defs = []
    for mc in [(serial.MetaClass, onto.classes), (serial.MetaProperty, onto.object_properties), (serial.MetaDataProperty, onto.data_properties)]:
        for c in mc[1]():
            meta_defs.append((c.iri,mc[0].iri))
    return meta_defs

def generate_serialization_contents(serialization_label, serialization_iri, mappings):
    X = ET.Element("NamedIndividual")
    X.set("rdf:about", serialization_iri)
    q = ET.SubElement(X,"rdf:type")
    q.set("rdf:resource", serial.Serialization.iri)
    for m in mappings:
        q = ET.SubElement(X,"ser:ContainsMapping")
        q.set("rdf:resource", m[0])
        
    q = ET.SubElement(X,"rdfs:label")
    q.text=serialization_label
    return X


def construct_translation_mapping(serialization_iri, translation_mapping_name, translation_mapping_dict):
    X = ET.Element("NamedIndividual")
    X.set("rdf:about", serialization_iri + uuid.uuid4().hex)
    q = ET.SubElement(X,"rdf:type")
    q.set("rdf:resource", serial.TranslationMapping.iri)
    q = ET.SubElement(X,"rdfs:label")
    q.text=translation_mapping_name
    
    for k,v in translation_mapping_dict.items():
        item_element = ET.SubElement(X, "NamedIndividual")
        item_element.set("rdf:about", serialization_iri + uuid.uuid4().hex)
        item_key = ET.SubElement(item_element, "ser:Key")
        item_key.text=k
        item_value = ET.SubElement(item_element, "ser:Value")
        item_value.text=v
    
    return X        
        
    
def generate_elemtree_header(serialization_label, serialization_iri, namespaces, ontology, mappings, translation_mappings):
    X = ET.Element('rdf:RDF')
    default_namespace='http://www.company.com'
    for prefix, uri  in namespaces:
        X.set("xmlns:" + prefix, uri)
    test = ET.tostring(X).decode()
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
              serial.MappingKVPair.iri ]:
        q = ET.SubElement(X, "Class")
        q.set("rdf:about", iri)
    
    comment = """///////////////////////////////////////////////////////////////////////////////////////
    //
    // Annotation properties - these should remain static
    // These are the internal technical components used by the loading/serialization process
    // that map onto the Serialization Ontology's Data Properties
    //
    ///////////////////////////////////////////////////////////////////////////////////////"""
    c = ET.Comment(comment)
    X.append(c)
    test = ET.tostring(X).decode()
    for iri in [ serial.ContainsMapping.iri,               
                 serial.MappingMetaTarget.iri,
                 serial.MappingDomain.iri,
                 serial.MappingRange.iri,
                 serial.MappingMetaTarget.iri,
                 serial.SerializationLabel.iri,
                 serial.SerializationParentLabel.iri, 
                 serial.Key.iri, 
                 serial.Value.iri]:
        q = ET.SubElement(X, "AnnotationProperty")
        q.set("rdf:about", iri)
        print (iri)
    test = ET.tostring(X).decode()    
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
    test = ET.tostring(X).decode()
    for iri,tp in generate_meta_definitions(ontology):
        q = ET.SubElement(X, "NamedIndividual")
        q.set("rdf:about", iri)
        p = ET.SubElement(q, "rdf:type")
        p.set("rdf:resource", tp)
    test = ET.tostring(X).decode()     
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
    X.append(c)

    for m in mappings:
        X.append(m[1])

    if len(translation_mappings)>0:
        comment = """   
        ///////////////////////////////////////////////////////////////////////////////////////
        //
        // Translation Mappings - optional static decode tables used to translate from input
        // values found in the serialization to target values expected by the ontology.
        //
        ///////////////////////////////////////////////////////////////////////////////////////"""
        c = ET.Comment(comment)
        X.append(c)

        print("\\\\\\\\TRANSLATION MAPPINGS\\\\\\\\\\")
        for t in translation_mappings:
            print (t)
            X.append(t)



    comment = """   
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Serialization - define the named Serialization Object and assign the set of 
    // mappings that belong to that object.
    //
    ///////////////////////////////////////////////////////////////////////////////////////"""
    c = ET.Comment(comment)
    X.append(c)

    X.append(generate_serialization_contents(serialization_label, serialization_iri, mappings))

    ET.indent(X, space="\t", level=0)
    return X

def find_match(value, match_set_list):
    for e,t_set in enumerate(match_set_list):
        if value in t_set:
            return e
    return None
        


def process_serialisation(json_data):
    s_label = json_data['serialization_label']
    s_iri = json_data['serialization_iri']
    s_onto = json_data['targetOntology']
    _fix_me_ontology_file = "../sample_ontology.owl"
    ontol = owlr.get_ontology(_fix_me_ontology_file).load()
    uri_base = ontol.base_iri
    
    ns_map = [('',"http://www.w3.org/2002/07/owl#"),
              ('xml:base',"http://www.w3.org/2002/07/owl"),
              ('rdf',"http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
              ('xml:owl',"http://www.w3.org/2002/07/owl#"),
              ('dc',"http://purl.org/dc/elements/1.1/"),
              ('rdfs',"http://www.w3.org/2000/01/rdf-schema#"), 
              ('ser', serial.base_iri)
             ]

    o_classes = [c.iri for c in ontol.classes()]
    o_properties =[p.iri for p in ontol.object_properties()]
    o_dataproperties = [d.iri for d in ontol.data_properties()]
    t_classes, t_properties, t_data_properties = json_data['targetClasses'], json_data['targetProperties'], json_data['targetDataProperties']
    # Optional Fetch of StaticProperties
    t_static_properties = json_data.get('targetStaticProperties', [])
    if all([c in o_classes for c in t_classes]):
        print("classes ok")
    else:
        print(set(o_classes).symmetric_difference(set(t_classes)))
        
    if all([c in o_properties for c in t_properties]):
        print("properties ok")
    else:
        print(set(o_properties).symmetric_difference(set(t_properties)))
        
        
    if all([d in o_dataproperties for d in t_data_properties]):
        print("data properties ok")
    else:
        print(set(o_dataproperties).symmetric_difference(set(t_data_properties)))
    #print (t_classes, t_properties, t_data_properties)
    mapping_list = []
    for mapping in json_data['serialization_mappings']:
        t_match=find_match(mapping['target'],[t_classes, t_properties, t_data_properties, t_static_properties])
        print(mapping, t_match)
        mapping_name = "".join([uri_base, mapping['mapping_name']])
        match t_match:
            case 0:
                # Classes
                properties = {k:v for k,v in {"ser:SerializationLabel" : mapping.get("label"),
                              "ser:SerializationParentLabel" : mapping.get("parent_label")}.items() if v is not None}
                
                mapping_list.append((mapping_name, create_mapping(mapping_name, mapping['target'], t_match, properties)))
            case 1:
                # Properties
                properties = {k:v for k,v in {"ser:MappingDomain" : mapping.get("domain"),
                              "ser:MappingRange" : mapping.get("range")}.items() if v is not None}
                mapping_list.append((mapping_name,create_mapping(mapping_name, mapping['target'], t_match, properties)))
                
            case 2:
                # Data Properties
                properties = {k:v for k,v in {"ser:MappingDomain" : mapping.get("domain"),
                              "ser:MappingRange" : mapping.get("range")}.items() if v is not None}
                mapping_list.append((mapping_name,create_mapping(mapping_name, mapping['target'], t_match, properties)))
            case 3:
                # Static Properties
                properties = {k:v for k,v in {"ser:MappingDomain" : mapping.get("domain"),
                              "ser:MappingRange" : mapping.get("range"),
                              "ser:TranslationMappingName" : mapping.get("translation_mapping_name")}.items() if v is not None}
                mapping_list.append((mapping_name,create_mapping(mapping_name, mapping['target'], t_match, properties)))
                print( properties )
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
    
    translation_mapping_list = []
    for t_mapping_name, t_mapping_content in json_data.get("translation_mappings",{}).items():
        
        translation_mapping_list.append(construct_translation_mapping(uri_base, t_mapping_name, t_mapping_content))

    X = generate_elemtree_header(s_label, s_iri, ns_map, ontol, mapping_list, translation_mapping_list)
                
    return X