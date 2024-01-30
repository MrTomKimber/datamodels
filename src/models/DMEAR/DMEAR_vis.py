from rdflib import URIRef, Graph, Namespace
from rdflib.util import from_n3
import pydotplus
from rdflib.tools.rdf2dot import rdf2dot
import difflib

def DMEAR_vizdiff_to_graph(S1, S2, option_dict=None, engine="dot", graph_options=None, v_type="png"):
    g = pydotplus.graph_from_dot_data(DMEAR_vizdiff_to_dot(S1, S2, option_dict, graph_options))
    try:
        output = g.create(prog=engine, format=v_type)
    except Exception as e:
        print (g.to_string())
        print(e)
        raise e


    
    return output
        
    



def typed_dictionary_from_triples(triple_set):
    type_d={}
    for t in triple_set:
        if t[1]==URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"):
            if t[2] not in type_d.keys():
                type_d[t[2]]=set([t[0]])
            else:
                type_d[t[2]].add(t[0])
                
    return type_d


def diffset(S1, S2):
    # Given two input sets, s1 and s2, return the Left difference, Intersection and Right difference between them
    L = S1.difference(S2)
    I = S1.intersection(S2)
    R = S2.difference(S1)
    return L,I,R


def LIR_test(triple, LIR_tuple):
    for e,s in enumerate(LIR_tuple):
        if triple in s:
            return e
    return None
    

def property_per_entity(triple_set, entity):
    property_d={}
    for t in triple_set:
        if t[0] == entity:
            if t[1] not in property_d.keys():
                property_d[t[1]]=set([t[2]])
            else:
                property_d[t[1]].add(t[2])
    return property_d


def retrieve_property_meta(triple_set, LIR_tuple, subject, predicate):
    meta_collection=[]
    for s,p,o in triple_set:
        if s==subject and p==predicate:
            LIR_loc=LIR_test((s,p,o), LIR_tuple)
            meta_collection.append((LIR_loc, o))
    return meta_collection



def DMEAR_attribute_string(parent_lir, attr_obj, option_dict=None, header=False):
    fg_col_dir = { 0 : "#880606", 1 : "#000000", 2 : "#068806", 3 : "#BB3333"}
    alt_col_dir = { 0 : "#EE8888", 1 : "#AAAAAA", 2 : "#88EE88", 3 : "#FFAAAA"}
    option_dict_keys = [("u_label", "Key", 0) , ("label", "Attribute", 0),  ("desc", "Description", 1), ("datatype", "DataType", 1), ("optionality","O/M", 1), ("pk","Is PK", 1)]
    if option_dict is None:
        option_dict = { "u_label" : False, 
                        "label" : True, 
                        "desc" : False, 
                        "optionality" : True, 
                        "pk" : True, 
                        "datatype" : True }
    
    attrstr = "<tr>"
    parent_col = fg_col_dir.get(parent_lir,3)
    bg_col = alt_col_dir.get(parent_lir,3)
    if attr_obj is None and header==True:
        attr_obj={}
    att_lir = attr_obj.get("lir",3)
    a_col = fg_col_dir.get(att_lir)
    for k,l,t in option_dict_keys:
        if option_dict[k]!=False:
            if header:
                hstr = """<td align='left' bgcolor='{bg_col}'><font point-size='12' color='#000000'><B>{a}</B></font></td>""".format(bg_col=bg_col, a=l)
                attrstr = attrstr + hstr
            else:
                vallist = attr_obj.get(k,"None")
                
                if t == 0:
                    # uniquely keyed type, source from singular input - there should only be a single value of this type.
                    if len(vallist)!=1:
                        assert False
                    else:
                        a_lir = att_lir
                        a_val = attr_obj.get(k,[(0,"None")])[0][1]
                        attr_col = a_col
                        # Ident Values get strikethrough markup treatment:
                        if a_lir==0:
                            a_val = "<s>" + a_val + "</s>"
                        markup = """<font point-size='12' color='{attr_col}'>{value}</font>""".format(attr_col=attr_col, value=a_val)
                        
                elif t == 1:
                    # Multiple values potentially exist, perform a textual-diff on the extracted contents
                    #markup_text_diffs
                    a_lir = att_lir
                    
                    a_val = attr_obj.get(k,[(0,"")])
                    text_b = "".join([t for l,t in a_val if l in (1,2)])
                    text_a = "".join([t for l,t in a_val if l == 0])
                    if len(text_b.strip())!=0 and len(text_a.strip())!=0:
                        markup_text = markup_text_diffs(text_a, text_b, fg_col_dir )
                        markup = """<font point-size='12'>{markup}</font>""".format(markup= markup_text)
                    else:
                        if len(text_b.strip())>0:
                            markup = """<font point-size='12' color='{attr_col}'>{value}</font>""".format(attr_col=attr_col, value=text_b)
                        elif len(text_a.strip())>0 and att_lir == 0:
                            markup = """<font point-size='12' color='{attr_col}'><s>{value}</s></font>""".format(attr_col=attr_col, value=text_a)
                        elif len(text_a.strip())>0 and att_lir == 1:
                            markup = """<font point-size='12' color='{attr_col}'>{value}</font>""".format(attr_col=attr_col, value=text_a)
                        else:
                            markup = ""

                
                attrstr = attrstr + f"""<td align='left'>{markup}</td>""".format(markup=markup)

    attrstr = attrstr + "</tr>"

    return attrstr


    attrstr = f"""<tr><td align='left' bgcolor='{alt_col}'><font point-size='12' color='#000000'><B>Attribute</B></font></td><td align='left' bgcolor='{alt_col}'><font point-size='12' color='#000000'><B>Identifier</B></font></td></tr>"""
    
    attrstr = f"""<tr><td align='left'><font point-size='12' color='{attr_col}'>{attr}</font></td><td align='left'><font point-size='12' color='{attr_col}'>{pk}</font></td></tr>"""

    


def DMEAR_vizdiff_to_dot(S1, S2, option_dict=None, graph_options_dict=None):

    if option_dict is None:
        option_dict = { "u_label" : False, 
                "label" : True, 
                "desc" : False, 
                "optionality" : True, 
                "pk" : True, 
                "datatype" : True }
    rdf_type_uri = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    class_uri = URIRef('http://www.tkltd.org/ontologies/datamodel#Class')
    relation_uri = URIRef('http://www.tkltd.org/ontologies/datamodel#Relationship')
    attribute_uri = URIRef('http://www.tkltd.org/ontologies/datamodel#Attribute')
    L, I, R = diffset(S1, S2)
    obj_dict = typed_dictionary_from_triples(S1.union(S2))
    entities=[]
    ent_node_dir={}
    DMEAR_types = [ URIRef('http://www.tkltd.org/ontologies/datamodel#Model'), 
                    URIRef('http://www.tkltd.org/ontologies/datamodel#Class'),
                    URIRef('http://www.tkltd.org/ontologies/datamodel#Attribute'), 
                    URIRef('http://www.tkltd.org/ontologies/datamodel#Relationship')
                    ]
    for e,entity in enumerate(obj_dict[class_uri]):
        node_name=f"node_{e}"
        ent_node_dir[entity]=node_name
        def_triple = (entity, rdf_type_uri, class_uri)
        LIR_loc = LIR_test(def_triple, (L,I,R))
        eprops = property_per_entity(S1.union(S2), entity)
        unique_ids = retrieve_property_meta(S1.union(S2), (L,I,R), entity, URIRef('http://www.tkltd.org/ontologies/serialization#UniqueIdentifier'))
        labels = retrieve_property_meta(S1.union(S2), (L,I,R), entity, URIRef('http://www.w3.org/2000/01/rdf-schema#label'))
        descriptions = retrieve_property_meta(S1.union(S2), (L,I,R), entity, URIRef('http://www.tkltd.org/ontologies/datamodel#Description'))
        content_elements = retrieve_property_meta(S1.union(S2), (L,I,R), entity, URIRef('http://www.tkltd.org/ontologies/datamodel#ClassContainsAttribute'))
        # possible filter on content_elements having type-assignments of Attribute
        attr_elements = []
        for a_lir, attribute in content_elements:
            aprops = property_per_entity(S1.union(S2), attribute)
            a_labels = retrieve_property_meta(S1.union(S2), (L,I,R), attribute, URIRef('http://www.w3.org/2000/01/rdf-schema#label'))
            a_descs = retrieve_property_meta(S1.union(S2), (L,I,R), attribute, URIRef('http://www.tkltd.org/ontologies/datamodel#Description'))
            a_dtypes = retrieve_property_meta(S1.union(S2), (L,I,R), attribute, URIRef('http://www.tkltd.org/ontologies/datamodel#DataType'))
            a_uniques = retrieve_property_meta(S1.union(S2), (L,I,R), attribute, URIRef('http://www.tkltd.org/ontologies/serialization#UniqueIdentifier'))
            a_optionalities = retrieve_property_meta(S1.union(S2), (L,I,R), attribute, URIRef('http://www.tkltd.org/ontologies/datamodel#Optionality'))
            a_pks = retrieve_property_meta(S1.union(S2), (L,I,R), attribute, URIRef('http://www.tkltd.org/ontologies/datamodel#isIdentifierForClass'))
            attribute_package = {"uri" : attribute, 
                                 "parent_lir" : LIR_loc, 
                                 "lir" : a_lir, 
                                 "u_label" : a_uniques, 
                                 "label" : a_labels, 
                                 "desc" : a_descs, 
                                 "datatype" : a_dtypes, 
                                 "optionality" : a_optionalities, 
                                 "pk" : a_pks}
            attr_elements.append(attribute_package)
            
        entity_package = {"uri" : entity, 
                          "node" : node_name, 
                          "lir" : LIR_loc, 
                          "u_label" : unique_ids, 
                          "label" : labels, 
                          "desc" : descriptions, 
                          "attributes" : attr_elements}
        
        entities.append(entity_package)
    
    
    relations=[]
    
    for relation in obj_dict[relation_uri]:

        rel_triple = (relation, rdf_type_uri, relation_uri)
        rel_lir = LIR_test(rel_triple, (L,I,R))
        rel_props = property_per_entity(S1.union(S2), relation)

        rel_from_class = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.tkltd.org/ontologies/datamodel#RelationshipFromClass'))
        rel_to_class = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.tkltd.org/ontologies/datamodel#RelationshipToClass'))
        rel_from_cardinality = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.tkltd.org/ontologies/datamodel#RelationshipFromCardinality'))
        rel_to_cardinality = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.tkltd.org/ontologies/datamodel#RelationshipToCardinality'))
        rel_from_attribute = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.tkltd.org/ontologies/datamodel#RelationshipFromAttribute'))
        rel_to_attribute = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.tkltd.org/ontologies/datamodel#RelationshipToAttribute'))
        rel_unique = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.tkltd.org/ontologies/serialization#UniqueIdentifier'))
        rel_label = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.w3.org/2000/01/rdf-schema#label'))
        rel_descs = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.tkltd.org/ontologies/datamodel#Description'))
        rel_type = retrieve_property_meta(S1.union(S2), (L,I,R), relation, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'))
        rel_package = {"uri" : relation, 
                       "lir" : rel_lir, 
                       "u_label" : rel_unique, 
                       "label" : rel_label, 
                       "desc" : rel_descs,
                       "from_class" : rel_from_class, 
                       "to_class" : rel_to_class, 
                       "from_node" : ent_node_dir[rel_from_class[0][1]],
                       "to_node" : ent_node_dir[rel_to_class[0][1]],
                       "from_attribute" : rel_from_attribute, 
                       "to_attribute" : rel_to_attribute, 
                       "from_cardinality" : rel_from_cardinality, 
                       "to_cardinality" : rel_to_cardinality,
                       "rel_type" : rel_type}
        
        relations.append(rel_package)
    
    
    ## Build up entities and relations in dot language

        

    
    #col_dir = { 0 : "'#068806'", 1 : "'#000000'", 2 : "'#880606'"}
    col_dir = { 0 : "RED", 1 : "BLACK", 2 : "GREEN"}
    fg_col_dir = { 0 : "#880606", 1 : "#000000", 2 : "#068806"}
    alt_col_dir = { 0 : "#EE8888", 1 : "#AAAAAA", 2 : "#88EE88"}
    #start = """digraph { \n graph [fontname = "helvetica"]; \n node [ fontname="DejaVu Sans" ] ; \n edge [fontname = "helvetica"]; \n"""

    if graph_options_dict is None:
        start = """digraph { \n graph [fontname = "helvetica"]; \n node [ fontname="helvetica" ] ; \n edge [fontname = "helvetica"]; \n"""
    else:
        g_opts = "\n ".join(["{k}={v};".format(k=k,v=v) for k,v in graph_options_dict.items()])
        start = "digraph {{ \n {g_opts} graph [fontname = \"helvetica\"]; \n node [ fontname=\"helvetica\" ] ; \n edge [fontname = \"helvetica\"]; \n".format(g_opts=g_opts)

    
     
 
 
    ent_content = ""
    for ents in entities:
        att_content=""
        
        node, col, alt_col, label, uri, desc = ents["node"], col_dir[ents["lir"]], alt_col_dir[ents["lir"]], ents["label"][0][1], ents["uri"], ents["desc"]
                    
        #"<br/>".join(text_utils.ww(html.escape(ents["desc"][0][1]),40))
        istest=True
        if istest:
            if len (ents["attributes"])>0:
                attrstr = DMEAR_attribute_string(ents["lir"], None, option_dict=option_dict, header=True) 
                att_content=att_content+attrstr
        else:
            if len (ents["attributes"])>0:
                # Set header for attribute table
                attrstr = f"""<tr><td align='left' bgcolor='{alt_col}'><font point-size='12' color='#000000'><B>Attribute</B></font></td><td align='left' bgcolor='{alt_col}'><font point-size='12' color='#000000'><B>Identifier</B></font></td></tr>"""
                att_content=att_content+attrstr

        e_sort={"\"Yes\"":0, "\"No\"": 1}

        for att in sorted(ents["attributes"], key=lambda x : (e_sort[x["pk"][0][1].n3()], x["u_label"][0][1].n3())):

            if istest:
                attrstr = DMEAR_attribute_string(ents["lir"], att, option_dict=option_dict, header=False) 

            else:

                
                attr=att["label"][0][1]
                pk=att["pk"][0][1]
                attr_lir = att["lir"]
                
                attr_col=fg_col_dir[attr_lir]

                if attr_lir != 0:
                    attrstr = f"""<tr><td align='left'><font point-size='12' color='{attr_col}'>{attr}</font></td><td align='left'><font point-size='12' color='{attr_col}'>{pk}</font></td></tr>"""
                else:
                    attrstr = f"""<tr><td align='left'><font point-size='12' color='{attr_col}'><s>{attr}</s></font></td><td align='left'><font point-size='12' color='{attr_col}'><s>{pk}</s></font></td></tr>"""
            att_content=att_content+attrstr


        entstr = f"""{node} [ shape=none, color={col} label=< <table color='{alt_col}'
         cellborder='1' cellspacing='0' border='1'><tr>
        <td colspan='2' bgcolor='{alt_col}'><B>{label}</B></td></tr><tr>
        <td href='{uri}' bgcolor='#ffffff' colspan='2' ALIGN='center'>
        <font point-size='10' color='#000000'>{desc}</font>
        </td>
        </tr>{att_content}</table> > ] \n"""

        ent_content = ent_content + entstr
            
    
    relstr = ""

    
    for rels in relations:
        fromnode, tonode, rel_col, rel_label = rels["from_node"], rels["to_node"], col_dir[rels["lir"]], rels["label"][0][1].n3()
        fg_rel_col = fg_col_dir[rels["lir"]]
        if rels["lir"]!=0:
            relstr = relstr + f"""\t{fromnode} -> {tonode} [ color={rel_col}, label=< <font point-size='10' color='{fg_rel_col}'>{rel_label}</font> > ] ;\n"""
        else:
            relstr = relstr + f"""\t{fromnode} -> {tonode} [ color={rel_col}, label=< <font point-size='10' color='{fg_rel_col}'><s>{rel_label}</s></font> > ] ;\n"""
        
    return start  + relstr + ent_content + "}"


def markup_text_diffs(text_a, text_b, col_dir_mapping):
    
    diffs = difflib.SequenceMatcher(None, text_a,text_b)

    output=""
    min_len=min(len(text_a), len(text_b))
    opcodes = diffs.get_opcodes()
    diff_ratio = len(opcodes)/(min_len+1)

    if len(opcodes)>4 or diff_ratio > 0.2:

        output=output+"""<font color=\"{old_col}\"><s>{content_old}</s></font><font color=\"{new_col}\">{content_new}</font>""".format(old_col=col_dir_mapping[0], content_old = text_a, new_col=col_dir_mapping[2], content_new=text_b)
    else:

        
        for c, i1, i2, j1, j2 in opcodes:
            if c in ["replace", "delete"]:

                content_old = text_a[i1:i2]
                content_new = text_b[j1:j2]
                if len(content_old)>0 and len(content_new)>0:
                    output=output+"""<font color=\"{old_col}\"><s>{content_old}</s></font><font color=\"{new_col}\">{content_new}</font>""".format(old_col=col_dir_mapping[0], content_old = text_a[i1:i2], new_col=col_dir_mapping[2], content_new=text_b[j1:j2])
                else:

                    assert c == "delete"
                    output=output+"""<font color=\"{old_col}\"><s>{content_old}</s></font>""".format(old_col=col_dir_mapping[0], content_old = text_a[i1:i2])

            elif c in "insert":

                content = text_b[j1:j2]
                if len(content)>0:
                    output=output+"""<font color=\"{new_col}\">{content}</font>""".format(new_col=col_dir_mapping[2], content = text_b[j1:j2])
                else:
                    output=content
            else:

                output=output+text_b[j1:j2]
    return output
