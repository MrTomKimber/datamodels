


def mermaid_escape_str(mstring : str) -> str:
    # Replace double-quotes with single quotes, and replace new-line chars with spaces.
    return mstring.replace("\"", "''").replace("\n", " ")


def get_keys_string(pk, fk, nulls):
    scenario=0
    if pk.lower()=="yes":
        scenario=1
    if fk.lower()=="yes":
        scenario=scenario+2

    if scenario == 0:
        return ""
    elif scenario == 1:
        return "PK"
    elif scenario == 2:
        return "FK"
    elif scenario == 3:
        return "PK, FK"

    return None
        


def format_erd_attribute(datatype : str, attribute : str, keys : str, description : str) -> str:
    indent="\t"
    datatype = mermaid_escape_str(datatype)
    attribute = mermaid_escape_str(attribute)
    keys = mermaid_escape_str(keys)
    description = mermaid_escape_str(description)
    return """{indent}{indent}{datatype} {attribute} {keys} \"{description}\" """.format(indent=indent, 
                                                                                         datatype=datatype, 
                                                                                         attribute=attribute, 
                                                                                         keys=keys, 
                                                                                         description=description)
    
    

def format_erd_node(entity : str, attributes : list, optional_alias  : str = None ) -> str:
    indent="\t"
    if optional_alias is None:
        optional_alias=""
    p_attributes = []
    for a in attributes:
        pass_attributes=[a["type"], 
                         a["name"],
                         get_keys_string(a["isPK"],a["isFK"], a["nulls"]),
                         a["description"]]
        p_attributes.append(format_erd_attribute(*pass_attributes))
    attributes = "\n".join(p_attributes)
    return """{indent}{entity}{optional_alias} {{
    {attributes}
    {indent}}}""".format(indent=indent, entity=entity, optional_alias=optional_alias, attributes=attributes)


def get_erd_relationship_end_token(left : bool, one : bool, nulls : bool ):
    if nulls:
        o_token = "o"
    else:
        o_token = "|"

    if one:
        c_token = "|"
    elif (not one and left):
        c_token = "}"
    elif (not one and not left):
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


def format_erd_relationship(relationship : str, left : str, right : str, left_cardinality : str , left_nulls : str, right_cardinality : str, right_nulls : str):
    
    lt = get_erd_relationship_end_token(True, 
                                        decode_cardinality_one_from_string(left_cardinality),
                                        decode_nulls_option_from_string(left_nulls))
    rt = get_erd_relationship_end_token(False, 
                                        decode_cardinality_one_from_string(right_cardinality),
                                        decode_nulls_option_from_string(right_nulls))
    
    return "{left} {lt}--{rt} {right} : {relationship}".format(left=left, right=right, lt=lt, rt=rt, relationship=relationship)
    

