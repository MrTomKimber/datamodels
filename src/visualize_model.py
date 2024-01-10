import io
import pydotplus
from rdflib.tools.rdf2dot import rdf2dot
from IPython.display import display, Image
import difflib

def visualize(g):
    stream = io.StringIO()
    rdf2dot(g, stream, opts = {display})
    #print(stream.getvalue())
    dg = pydotplus.graph_from_dot_data(stream.getvalue())
    png = dg.create_png()

    display(Image(png))

def t2rdflibg(triples): #triples to rdflib graph
    g = Graph()
    for t in triples:
        g.add(t)
    return g

def get_field(v):
    if isinstance(v,str):
        return html.escape(str(v))
    elif isinstance(v,(int, float)):
        if pd.isnull(v):
            return None
        else:
            return v
    elif v is None or isinstance(v,pd.Null):
        return None
    
def markup_text_diffs(text_a, text_b):
    diffs = difflib.SequenceMatcher(None, text_a,text_b)
    output=""
    for c, i1, i2, j1, j2 in diffs.get_opcodes():
        if c in ["replace", "delete"]:
            #print(c, b[j1:j2])
            output=output+"<font color=\"red\"><s>"+text_a[i1:i2]+"</s></font>"+"<font color=\"green\">" + text_b[j1:j2]+"</font>"
        elif c in "insert":
            #print(c, b[j1:j2])
            output=output+"<font color=\"green\">" + text_b[j1:j2]+"</font>"
        else:
            #print(c, b[j1:j2])
            output=output+text_b[j1:j2]
    return output

