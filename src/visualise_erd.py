import gravis as gv
import graphviz
import networkx as nx
from urllib.parse import urlparse
import textwrap
import re
import base64
from qt_utils import qt_dict
from rdflib import URIRef, Literal

def class_graphviz_table_constructor(classdef):
    wordwrap_max_length=60
    identifier = " ".join(classdef.get("identifier"))
    label = html_wordwrap(" ".join(classdef.get("label")),wordwrap_max_length)
    description = html_wordwrap(" ".join(classdef.get("description")),120)

    d_row="""        <tr>
            <td colspan="5" bgcolor='grey'><font point-size='32' color='#ffffff'><B>{label}</B></font></td>
             </tr>
              <tr>
            <td colspan="5" ALIGN="LEFT" BALIGN="LEFT">{description}</td>
        </tr>""".format(label=label, description=description)
   # d_row=""

    class_d = {"identifier":identifier, 
          "label":label, 
          "description":description, 
          "d_row":d_row}

    table = """< <table id="{identifier}" BORDER="0" CELLBORDER="1" CELLSPACING="0" STYLE="ROUNDED">

    {d_row}
        <tr><td><B>Attribute</B></td><td><B>Description</B></td><td ><B>Datatype</B></td><td ><B>Nulls</B></td><td ><B>PK</B></td></tr>

    {rows}

    </table>>"""
    rows = []
    rowdef = """<tr><td >{alabel}</td><td>{adescription}</td><td >{adatatype}</td><td >{anulls}</td><td >{apk}</td></tr>\n"""
    rowdef = """<tr><td ALIGN="LEFT" BALIGN="LEFT"><B>{alabel}</B></td><td ALIGN="LEFT" BALIGN="LEFT">{adescription}</td><td>{adatatype}</td><td>{anulls}</td><td >{apk}</td></tr>\n"""
    
#    for i,a in sorted([(i,a) for i,a in classdef.get("attributes").items() if "".join(a['pk']).lower()=="yes"],key=lambda x : "".join(x[1]['label'])):
#        a_dict={"alabel":html_wordwrap(" ".join(a.get('label')),wordwrap_max_length),
#        "adescription":html_wordwrap(" ".join(a.get('description')),wordwrap_max_length),
#        "adatatype":html_wordwrap(" ".join(a.get('datatype')),wordwrap_max_length),
#        "anulls":html_wordwrap(" ".join(a.get('nulls')),wordwrap_max_length),
#        "apk":html_wordwrap(" ".join(a.get('pk')),wordwrap_max_length)}
#        rows.append(rowdef.format(**a_dict))

    for i,a in sorted([(i,a) for i,a in classdef.get("attributes").items() ],key=lambda x : "".join(x[1]['sequence'])):
        a_dict={"alabel":html_wordwrap(" ".join(a.get('label')),wordwrap_max_length),
        "adescription":html_wordwrap(" ".join(a.get('description')),wordwrap_max_length),
        "adatatype":html_wordwrap(" ".join(a.get('datatype')),wordwrap_max_length),
        "anulls":html_wordwrap(" ".join(a.get('nulls')),wordwrap_max_length),
        "apk":html_wordwrap(" ".join(a.get('pk')),wordwrap_max_length)}
        rows.append(rowdef.format(**a_dict))
    rows = " ".join(rows)
    return table.format(**{**class_d, **{"rows":rows}})

def uriref2loc(uriref):
    p = urlparse(uriref.toPython())
    id = "/".join([p.netloc, p.path])
    return id

def dot_table_to_svg(id, tab_def):
    dot = graphviz.Graph()
    dot.node_attr['fontname']="DejaVu Sans"
    dot.node(id, label=tab_def, shape="plaintext")
    src = dot.pipe(format="dot").decode()
    return dot.pipe(format="svg", engine="dot"),src

def html_wordwrap(text, target_length):
    tw = textwrap.TextWrapper(width=target_length)
    return "<br/>".join(tw.wrap(text))

def collate_node_and_edge_features(graph):

    q_template={ "self" : "PARAMETER(@selfuri)",
    "contents" : {  "label" : "SPARQL(SELECT ?label WHERE {@selfuri <http://www.w3.org/2000/01/rdf-schema#label> ?label})", 
                    "type" : "SPARQL(SELECT ?type WHERE {@selfuri <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type})",
                    "description" : "SPARQL(SELECT ?description WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#Description> ?description})",
                    "identifier" : "SPARQL(SELECT ?identifier WHERE {@selfuri <http://www.tkltd.org/ontologies/serialization#UniqueIdentifier> ?identifier})",
                    "context" : """SPARQL(SELECT ?context WHERE { ?c rdf:type <http://www.tkltd.org/ontologies/datamodel#Context>. ?c rdfs:label ?context. ?c <http://www.tkltd.org/ontologies/datamodel#Contains> @selfuri . })""",
                    "@attributeuri" : "SPARQL(SELECT ?attributeuri WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#ClassContainsAttribute> ?attributeuri})",
                    "attributes" : { 
                        "self" : "PARAMETER(@attributeuri)",
                        "contents" : {
                            "label" : "SPARQL(SELECT ?label WHERE {@attributeuri <http://www.w3.org/2000/01/rdf-schema#label> ?label})", 
                            "datatype" : "SPARQL(SELECT ?datatype WHERE {@attributeuri <http://www.tkltd.org/ontologies/datamodel#DataType> ?datatype})",
                            "nulls" : "SPARQL(SELECT ?nulls WHERE {@attributeuri <http://www.tkltd.org/ontologies/datamodel#NullsOptional> ?nulls})",
                            "optionality" : "SPARQL(SELECT ?optionality WHERE {@attributeuri <http://www.tkltd.org/ontologies/datamodel#Optionality> ?optionality})",
                            "pk" : "SPARQL(SELECT ?pk WHERE {@attributeuri <http://www.tkltd.org/ontologies/datamodel#isIdentifierForClass> ?pk})",
                            "identifier" : "SPARQL(SELECT ?identifier WHERE {@attributeuri <http://www.tkltd.org/ontologies/serialization#UniqueIdentifier> ?identifier})",
                            "description" : "SPARQL(SELECT ?description WHERE {@attributeuri <http://www.tkltd.org/ontologies/datamodel#Description> ?description})",
                            "sequence" : "SPARQL(SELECT ?sequence WHERE {@attributeuri <http://www.tkltd.org/ontologies/datamodel#Sequence> ?sequence})",
                                    }
                                   }
                    }
                }
    q_relationship_template={ "self" : "PARAMETER(@selfuri)",
        "contents" : {  "label" : "SPARQL(SELECT ?label WHERE {@selfuri <http://www.w3.org/2000/01/rdf-schema#label> ?label})", 
                        "type" : "SPARQL(SELECT ?type WHERE {@selfuri <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type})",
                        "description" : "SPARQL(SELECT ?description WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#Description> ?description})",
                        "identifier" : "SPARQL(SELECT ?identifier WHERE {@selfuri <http://www.tkltd.org/ontologies/serialization#UniqueIdentifier> ?identifier})",
                        "fromclass" : "SPARQL(SELECT ?fclass WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#RelationshipFromClass> ?fclass})",
                        "toclass" : "SPARQL(SELECT ?tclass WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#RelationshipToClass> ?tclass})",
                        "fromattribute" : "SPARQL(SELECT ?fattr WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#RelationshipFromAttribute> ?fattr})",
                        "toattribute" : "SPARQL(SELECT ?tattr WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#RelationshipToAttribute> ?tattr})",
                        "fromcardinality" : "SPARQL(SELECT ?fcard WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#FromCardinality> ?fcard})",
                        "tocardinality" : "SPARQL(SELECT ?tcard WHERE {@selfuri <http://www.tkltd.org/ontologies/datamodel#ToCardinality> ?tcard})",
                        }
    }
    rdftype_uriref=URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')


    model_classes = []
    for s,p,o in graph.triples((None, rdftype_uriref, URIRef('http://www.tkltd.org/ontologies/datamodel#Class'))):
        model_classes.append(s)
    rel_classes=[]
    for s,p,o in graph.triples((None, rdftype_uriref, URIRef('http://www.tkltd.org/ontologies/datamodel#Relationship'))):

        rel_classes.append(s)

    class_dict = qt_dict(graph, q_template, {"@selfuri" : model_classes}, scope=None)
    rel_dict = qt_dict(graph, q_relationship_template, {"@selfuri" : rel_classes}, scope=None)

    return class_dict, rel_dict

def generate_static_dot_layout(graph):
    dot = graphviz.Graph(comment="test")


    dot.engine = 'dot' 
    dot.graph_attr['rankdir'] = 'LR' 
    dot.graph_attr['overlap'] = 'ortho' 
    #dot.graph_attr['model'] = 'subset' 
    dot.graph_attr['mode'] = 'hier' 
    dot.graph_attr['mode'] = 'ipsep' 
    #dot.graph_attr['beautify'] = 'true' 
    dot.graph_attr['center'] = 'true' 
    dot.graph_attr['splines'] = 'True' 
    dot.graph_attr['sep']='0.5'
    dot.graph_attr['esep']='0.1'
    #dot.graph_attr['size']='4,4!'
    #dot.graph_attr['ratio']='compress'
    dot.node_attr['fontname']="DejaVu Sans"

    class_dict,rel_dict = collate_node_and_edge_features(graph)

    class_tables={}

    subgraph_contents={}

    for c,v in class_dict.items():
        id = uriref2loc(c)
        class_tables[id]=class_graphviz_table_constructor(v)
        dot.node(id, label=class_tables[id], shape="plaintext")

    for r,v in rel_dict.items():
        dot.edge(uriref2loc(v['fromclass'][0]), uriref2loc(v['toclass'][0]), label=v['label'][0].toPython(), constraint='true')
    src = dot.pipe(format="dot", engine="dot")
    svg = dot.pipe(format="svg", engine="dot")
    image_data_url = """data:image/svg+xml;base64,{d}""".format(d=base64.b64encode(svg).decode("utf-8"))


    html_base = """
<div class="container" id="container" >

    <img src="{image_data_url}" width="1200" height="800" id="imageZoom" />
</div>
<script type="text/javascript">
let touchControl = new touchScriptController(
        document.getElementById('imageZoom'),   // Image Element
        document.getElementById('container'),   // Parent Container Element
        {{                                       // Options to preset the scale and translate
            scale: 1,
            translateX: 0,
            translateY: 0
        }});
</script>
<pre>
{dot_code}
</pre>
""".format(image_data_url=image_data_url, dot_code=src)
    return html_base



def process_graph(graph):

    class_dict,rel_dict = collate_node_and_edge_features(graph)

    class_tables={}
    for c,v in class_dict.items():
        id = uriref2loc(c)
        class_tables[id]=class_graphviz_table_constructor(v)
        #dot.node(id, label=class_tables[id], shape="plaintext")

    #for r,v in rel_dict.items():
        #dot.edge(uriref2loc(v['fromclass'][0]), uriref2loc(v['toclass'][0]), label=v['label'][0].toPython(), constraint='true')


    nx_g = nx.MultiGraph()
    find_bb_rx=re.compile("\[bb=\"([\d}]{1,6}),([\d}]{1,6}),([\d}]{1,6}),([\d}]{1,6})\"\]")

    for k,t in class_tables.items():
        png,src=dot_table_to_svg(k,t)
        table_image_data_url = """data:image/svg+xml;base64,{d}""".format(d=base64.b64encode(png).decode("utf-8"))
        x,y,w,h=[int(i)/5 for i in find_bb_rx.search(src).groups()]
        nx_g.add_node(k, label=k, **{"color" : "white", 
                                    "shape" : "rectangle", 
                                    "image" : table_image_data_url, 
                                    "size":max([w,h])})

    for r,v in rel_dict.items():
        #print(v['fromclass'][0].toPython(), v['toclass'][0].toPython(), v['label'][0].toPython())
        nx_g.add_edge(uriref2loc(v['fromclass'][0]), uriref2loc(v['toclass'][0]), label=v['label'][0].toPython(), constraint='true')
        
    gjgf = gv.convert.networkx_to_gjgf(nx_g)
    return gjgf

