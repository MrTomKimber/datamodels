import re
from rdflib import URIRef, Graph, Namespace, Literal


def to_text(something, context=None):
    if context is None:
        if isinstance(something, (URIRef, Literal)):
            return something.toPython()
        elif isinstance(something, str):
            return something
        else:
            return str(something)
    elif context=="sparql":
        if isinstance(something, (URIRef, Literal)):
            return something.n3()
        elif isinstance(something, str):
            return something
        else:
            return str(something)

def multi_replace(text, replace_parms, parameters):
    for p in replace_parms:
        text=text.replace(p, to_text(parameters.get(p, None), context="sparql"))
    return text

def resolve_content(graph, content, parameters, scope):
    # Given a string, unpack and resolve to some list of results
    # parameters hosts global list of parameter options, while
    # scope contains the current working values being processed
    value_type_rx=re.compile("(SPARQL|PARAMETER)\((.*)\)")
    match_groups=value_type_rx.findall(content)
    if match_groups is not None and len(match_groups)>0:
        m_type, m_value = match_groups[0]
    if m_type.lower()=="parameter":
        r_val = [m_value,parameters.get(m_value, None)]
        return r_val
    elif m_type.lower()=="sparql":
        get_parms_rx=re.compile("\@[\w]*")
        replace_parms = get_parms_rx.findall(m_value)
        query = multi_replace(m_value, replace_parms, scope)
        rs =  g.query(query)
        return [v[0] for v in list(rs)]
    

def qt_dict(graph, template, parameters, scope=None):
    """Run through a node_properties extract template, each section containing a
    self and contents section. 
    The self section defines a key value which is drawn from parameters and assigned to
    the scope. """
    return_d = dict()
    if scope is None:
        scope=dict()
    self_key_content = template.get('self', None)
    
    self_key_name, self_key_list=resolve_content(graph, self_key_content, parameters, scope)
    for key in self_key_list:
        return_d[key]=dict()
        scope[self_key_name]=key
        for header, specification in template.get('contents', {}).items():
            if not isinstance(specification, dict):
                resolved_content=resolve_content(graph, specification, parameters, scope)
                return_d[key][header]=resolved_content
                if header[0]=="@":
                    parameters={**parameters, **{header:resolved_content}}
            else:
                return_d[key][header]=qt_dict(graph, template.get('contents').get(header), parameters, scope)
    return return_d
