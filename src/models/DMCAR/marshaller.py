from dataclasses import dataclass
from pandas import DataFrame, isna
import re

def conform_to_string(value):
    if value is None:
        return ""
    else:
        if isinstance(value, str):
            return value
        elif isinstance(value, float):
            if isna(value):
                return ""
            else:
                return str(value)
        else:
            return str(value)

@dataclass
class Class:
    namespace : str
    name :str
    label : str
    description : str
    attributes : list = None

    def set_child_attributes(self, attribute_list):
        self.attributes=attribute_list
    
    @staticmethod
    def marshal_from_DMCAR(row):
        return Class(namespace=conform_to_string(row.Namespace), 
                       name=conform_to_string(row.Class), 
                       label=conform_to_string(row.ClassLabel), 
                       description=conform_to_string(row.ClassDescription))

        


@dataclass 
class Attribute:
    parent_class_name : str
    namespace : str
    name : str
    label : str
    description : str
    sequence : str
    datatype : str
    nulls : bool
    ispk : bool
    parent_class : Class = None

    def set_parents(self, classes : list[Class]):
        classnames_d = {".".join([c.namespace , c.name]):c for c in classes}
        self.parent_class = classnames_d.get(".".join([self.namespace , self.parent_class_name]), "{pclass} unassigned for attribute {attribute}".format(pclass=self.parent_class_name, attribute=self.name))

    @staticmethod
    def marshal_from_DMCAR(row) :
        return Attribute(namespace=conform_to_string(row.Namespace), 
                     parent_class_name=conform_to_string(row.Class),
                     name=conform_to_string(row.Attribute), 
                     label=conform_to_string(row.AttributeLabel), 
                     description=conform_to_string(row.AttributeDescription), 
                     sequence=conform_to_string(row.Sequence), 
                     datatype=conform_to_string(row.DataType), 
                     nulls=conform_to_string(row.Nulls),
                     ispk=conform_to_string(row.IsPK)
                    )


@dataclass
class Relationship:
    namespace : str
    name :str
    label : str
    description : str
    type : str
    from_namespace : str
    from_class_name : str
    from_cardinality : str
    from_cardinality_one : bool
    to_namespace : str
    to_class_name : str
    to_cardinality : str
    to_cardinality_one : bool
    from_class : Class = None
    from_attribute_name : str = None
    from_attribute : Attribute = None
    to_class : Class = None
    to_attribute_name : str = None
    to_attribute : Attribute = None

    def set_parents(self, classes : list[Class], attributes : list[Attribute]):
        classnames_d = {".".join([c.namespace , c.name]):c for c in classes}
        attrnames_d = {".".join([a.namespace , a.parent_class_name, a.name]):a for a in attributes}
        self.from_class = classnames_d.get(".".join([self.from_namespace , self.from_class_name]), "from: {fclass} unassigned for relationship {rel}".format(fclass=self.from_class_name, rel=self.name))
        self.to_class = classnames_d.get(".".join([self.to_namespace , self.to_class_name]), "to: {tclass} unassigned for relationship {rel}".format(tclass=self.from_class_name, rel=self.name))

        if not isna(self.from_attribute_name) and self.from_attribute_name.strip() != "":
            self.from_attribute = attrnames_d.get(".".join([self.from_namespace , self.from_class_name, self.from_attribute_name]), "unassigned")
            print(self.from_attribute, self.from_attribute_name)

        if not isna(self.to_attribute_name) and self.to_attribute_name.strip() != "":
            self.to_attribute = attrnames_d.get(".".join([self.to_namespace , self.to_class_name, self.to_attribute_name]), "unassigned")
            print(self.to_attribute, self.to_attribute_name)

    def marshal_from_DMCAR(row) :
        if conform_to_string(row.FromCardinality).lower() in ("one", "1", "None"):
            bool_from_cardinality_one = True
        else:
            bool_from_cardinality_one = False

        if conform_to_string(row.ToCardinality).lower() in ("one", "1", "None"):
            bool_to_cardinality_one = True
        else:
            bool_to_cardinality_one = False

            
        return Relationship(namespace=conform_to_string(row.Namespace), 
                     name=conform_to_string(row.Relationship), 
                     label=conform_to_string(row.RelationshipLabel), 
                     description=conform_to_string(row.RelationshipDescription), 
                     type=conform_to_string(row.RelationshipType), 
                     from_namespace=conform_to_string(row.FromNamespace), 
                     from_class_name=conform_to_string(row.FromClass), 
                     from_attribute_name=conform_to_string(row.FromAttribute), 
                     from_cardinality=conform_to_string(row.FromCardinality), 
                     from_cardinality_one=bool_from_cardinality_one, 
                     to_namespace=conform_to_string(row.ToNamespace), 
                     to_class_name=conform_to_string(row.ToClass), 
                     to_attribute_name=conform_to_string(row.ToAttribute), 
                     to_cardinality=conform_to_string(row.ToCardinality), 
                     to_cardinality_one=bool_to_cardinality_one


                    )

class MermaidWrapper:

    def escape_str(mstring : str) -> str:
        # Replace double-quotes with single quotes, and replace new-line chars with spaces.
        return mstring.replace("\"", "''").replace("\n", " ")


    def get_keys_string(attribute : Attribute):
        ## PK, FK and UK are all valid key settings per Mermaid - no UK available here however
        pk = attribute.ispk
        fk = False
        uk = False
        option_keys = ["PK", "FK", "UK"]
        return ",".join([k for e,k in enumerate(option_keys) if [pk,fk,uk][e]])

            


    def format_erd_attribute(attribute : Attribute) -> str:
        indent="\t"
        datatype = MermaidWrapper.escape_str(attribute.datatype)
        if datatype.strip() == "":
            # Set default value for blank datatype
            datatype = "_"
        attribute_name = MermaidWrapper.escape_str(attribute.name)
        keys = MermaidWrapper.escape_str(MermaidWrapper.get_keys_string(attribute))
        description = MermaidWrapper.escape_str(attribute.description)
        return """{indent}{indent}{datatype} {attribute} {keys} \"{description}\" """.format(indent=indent, 
                                                                                            datatype=datatype, 
                                                                                            attribute=attribute_name, 
                                                                                            keys=keys, 
                                                                                            description=description)
        
        

    def format_erd_node(entity : Class) -> str:
        indent="\t"
        p_attributes = []
        for a in sorted(entity.attributes, key=lambda a : a.sequence):
            p_attributes.append(MermaidWrapper.format_erd_attribute(a))

        attributes = "\n".join(p_attributes)
        return """{indent}{entity}[\"{optional_alias}\"] {{
        {attributes}
        {indent}}}""".format(indent=indent, entity=entity.name, optional_alias=entity.label, attributes=attributes)


    def get_erd_relationship_end_token(left : bool, relationship : Relationship):
        c_token = "|"
        o_token = "|"
        if left:
            if relationship.from_attribute is not None:
                if relationship.from_attribute.nulls:
                    o_token = "o"
                else:
                    o_token = "|"
            else:
                o_token = "o"

            if not relationship.from_cardinality_one:
                c_token = "}"
        else:
            if relationship.to_attribute is not None:
                print(relationship.to_attribute)
                if relationship.to_attribute.nulls:
                    o_token = "o"
                else:
                    o_token = "|"
            if not relationship.to_cardinality_one:
                c_token = "{"
        
        if left:
            return c_token + o_token
        else:
            return o_token + c_token

    def decode_cardinality_one_from_string(c_string):
        if c_string is not None:
            if c_string.lower() in "one":
                return True
            elif c_string.lower() in "many":
                return False
            else:
                return True
        else:
            return True    

    def decode_nulls_option_from_string(n_string):
        if n_string is not None:
            if str(n_string).lower() in ("yes", "true", "1"):
                return True
            elif str(n_string).lower() in ("no", "false", "0"):
                return False
            else:
                return False
        else:
            return False  


    def format_erd_relationship(relationship : Relationship):
        
        lt = MermaidWrapper.get_erd_relationship_end_token(True,relationship)
        rt = MermaidWrapper.get_erd_relationship_end_token(False,relationship)
        
        return "{left} {lt}--{rt} {right} : {relationship}".format(left=relationship.from_class_name, 
                                                                   right=relationship.to_class_name, 
                                                                   lt=lt, 
                                                                   rt=rt, 
                                                                   relationship="\"" + str(relationship.label) + "\"")
        



def popo_from_pandas(df : DataFrame):
    # Get raw Classes from DataFrame
    classes=[]
    for c in df.groupby("Class").groups:
        classes.append( Class.marshal_from_DMCAR(df.groupby("Class").get_group(c).iloc[0]))

    # Get raw Attributes from DataFrame
    attributes=[]
    for a in df.groupby(["Class", "Attribute"]).groups:
        if all([not isna(v) for v in a]):
            attribute = Attribute.marshal_from_DMCAR(df.groupby(["Class", "Attribute"]).get_group(a).iloc[0])
            attribute.set_parents(classes)
            attributes.append( attribute )

    for c in classes:
        a_list = [a for a in attributes if a.parent_class.name == c.name]
        c.set_child_attributes(a_list)

    relationships=[]
    for r in df.groupby(["Relationship"]).groups:

        relationship = Relationship.marshal_from_DMCAR(df.groupby("Relationship").get_group(r).iloc[0])
        relationship.set_parents(classes, attributes)
        relationships.append( relationship )

    return { "classes" : classes, 
             "attributes" : attributes, 
             "relationships" : relationships}

def mermaid_from_popo(popo : dict) -> str:
    mnodes=[]
    for n in popo['classes']:
        mnodes.append(MermaidWrapper.format_erd_node(n))

    mrels=[]
    for l in popo['relationships']:
        mrels.append(MermaidWrapper.format_erd_relationship(l))

    return """erDiagram\n """ + "\n".join(mnodes) + "\n".join(mrels)

