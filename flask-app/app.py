# Import flask module
from flask import Flask, flash, redirect, request, render_template_string, url_for
from werkzeug.utils import secure_filename
import jinja2
import pandas as pd


import os, sys
MODPATH=os.path.split(__file__)[0]
sys.path.append(os.path.join(MODPATH,"..","src"))

import repository
import vis_owl
import gravis as gv
from rdflib import Graph, URIRef, Literal, BNode

file_loader = jinja2.FileSystemLoader("templates/")
static_folder = jinja2.FileSystemLoader("static/")
env = jinja2.Environment(loader=file_loader)
template = env.get_template('page_template.jinja2')

UPLOAD_FOLDER="uploads/"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','rdf','owl','xlsx','csv'}

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

STORETYPE = 'jena'
QUERYENDPOINT="http://fuseki:3030/modelg/query"
UPDATEENDPOINT="http://fuseki:3030/modelg/update"
repo = repository.Repository(store_type=STORETYPE,query_url=QUERYENDPOINT, update_url=UPDATEENDPOINT)


@app.route('/')
def index():
    content = """index"""
    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           content=content)

@app.route('/view')
def view():
    content = """view"""
    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           content=content)

@app.route('/query', methods=['GET', 'POST'])
def query():
    if request.method == 'POST':
        q = request.form.get('querytext','')
        rs=repo.run_adhoc_query(q)
        rs_tab_html=pd.DataFrame(rs).to_html()
        #rs_tab_html=f"<p>{q}</p>"
    else:
        q="""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
PREFIX owl: <http://www.w3.org/2002/07/owl#> 

select ?g ?p (COUNT (?p) as ?triples)
    WHERE
    {GRAPH ?g { ?s ?p ?o. }
}
GROUP BY ?g ?p
ORDER BY ?g ?p"""

        rs_tab_html=""

    content = f"""<div><p><a href="https://sparql.org/query-validator.html" target="_blank" rel="noopener noreferrer">https://sparql.org/query-validator.html</a></p></div>
    
    <form method=post enctype=multipart/form-data method="post">
    <div><textarea name="querytext" id="querytext" rows="10" cols="50" onkeydown="if(event.keyCode===9){{var v=this.value,s=this.selectionStart,e=this.selectionEnd;this.value=v.substring(0, s)+'\t'+v.substring(e);this.selectionStart=this.selectionEnd=s+1;return false;}}">{q}</textarea></div>
    <div><input type=submit value=Query></div>
    </form>{rs_tab_html}"""

    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           content=content)



@app.route('/ontologies', methods=['GET', 'POST'])
def ontologies():

    q="""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
PREFIX owl: <http://www.w3.org/2002/07/owl#> 

select ?g ?ont ?label ?comment (COUNT (?p) as ?triples)
        
    WHERE
    {GRAPH ?g { ?ont a owl:Ontology. 
                OPTIONAL { ?ont rdfs:label ?label. 
                FILTER (langMatches(lang(?label),"en") || lang(?label)='')}
                OPTIONAL { ?ont rdfs:comment ?comment. 
                FILTER (langMatches(lang(?comment),"en") || lang(?label)='')} }
    GRAPH ?ont { ?s ?p ?o. }            
   VALUES ?g { <http://ontologies> }
}
GROUP BY ?g ?ont ?label ?comment 
 """
    rs=repo.run_adhoc_query(q)
    rs=repository.new_column_to_qr_from_function(rs,
                                      "Visualise",
                                      lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('ont')}" value="Visualise"/>""")
    rs=repository.new_column_to_qr_from_function(rs,
                                    "Delete",
                                    lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('ont')}" value="Delete"/>""")
    rs = repository.reorder_qr_columns(rs, {"Delete":"Delete", "Graph":"g", "Ontology" : "ont", "Label" :"label", "Comment" : "comment", "Triples" : "triples", "Visualise" : "Visualise"})
    rs_tab_html=repository.qr_to_html_table(rs)

    preamble = """<p>Show a list of imported ontologies currently hosted by the system and provide the option to visualise them.</p>
    <p>Additionally, provide a link where additional ontologies can be registered by uploading a file in rdf or owl format.</p>"""
    content = preamble + f"""<form method=post enctype=multipart/form-data method="post">
    <div>{rs_tab_html}</div>
    </form>
    <form action="/upload">
    <div><input type=submit value=Upload></div>
    </form>
    """

    if request.method == 'POST':
        content = str(request.form.to_dict())
        request_d = request.form.to_dict()
        if "Visualise" in request_d.values():
            o_graph_uri = set([d for d,k in request_d.items() if k=="Visualise"]).pop()
            q=f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
    PREFIX owl: <http://www.w3.org/2002/07/owl#> 

    select ?s ?p ?o
        WHERE
        {{GRAPH ?g {{ ?s ?p ?o. 
        VALUES ?g {{ <{o_graph_uri}> }} }}
    }}"""
            g = Graph()
            triples=repo.ds.query( q )
            for t in triples:
                g.add(t)
            #gjgf=vis_owl.gen_gjgf_from_owl_model_graph(g)
            content="<h1>Hello Freddie</h1>" + visualise(g.de_skolemize())
        elif "Delete" in request_d.values():
            d_graph_uri = set([d for d,k in request_d.items() if k=="Delete"]).pop()
            content = f"Going to delete! {d_graph_uri}"
            #repo.truncate_graph(d_graph_uri)
            q=f"""WITH <http://ontologies>
            DELETE {{ ?s ?p ?o }}
            WHERE {{ ?s ?p ?o.
            FILTER (?s=<{d_graph_uri}> )
            }}"""
            #rs=repo.ds.query(q)
            rs=repo.ds.update(q)
            rs_tab_html=f"deleted {d_graph_uri}"
            content=f"""<div>{rs_tab_html}</div>"""

    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           content=content)
   


@app.route('/admin')
def admin():
    content = """admin"""
    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           content=content)

def visualise(g):
    content = """visualise"""

    gjgf=vis_owl.gen_gjgf_from_owl_model_graph(g)

    model_html = gv.d3(gjgf, 
      node_label_data_source='label',
      show_edge_label=True,
      edge_label_size_factor=0.7,
      edge_label_data_source='label',
      edge_curvature=0.25,
     links_force_strength=0.1, 
     links_force_distance=100, 
     use_collision_force=True, 
     collision_force_radius=25, 
     many_body_force_strength=-500,
     ).to_html_partial()

    return model_html


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            g = owl_file_to_graph(file).skolemize()
            
#            vis = visualise(g)
            # Get ontology reference:
            ont_triples = list(g.triples((None, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef('http://www.w3.org/2002/07/owl#Ontology'))))
            if len(ont_triples)==1:
                ontology_uri = ont_triples[0][0]
                print(ontology_uri)
                # if graph exists then clear it
                label_list=[(s,p,o) for s,p,o in g.triples((ontology_uri, URIRef('http://www.w3.org/2000/01/rdf-schema#label'), None)) if (str(o.language).lower()=="en" or o.language is None) ]
                description_list=[(s,p,o) for s,p,o in g.triples((ontology_uri, URIRef('http://www.w3.org/2000/01/rdf-schema#comment'), None)) if (str(o.language).lower()=="en" or o.language is None)]
                label=None
                description=None
                if len(label_list)>0:
                    label = ".".join([l[2].toPython() for l in label_list if (not repo.detect_bnode(l[2])) and l[2].language=="en"])
                if len(description_list)>0:
                    description = ".".join([l[2].toPython() for l in description_list if not repo.detect_bnode(l[2]) and l[2].language=="en"])
                # Upload graph triples
                register_quads=[]
                register_quads.append((ontology_uri, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef('http://www.w3.org/2002/07/owl#Ontology')))
                if label is not None:
                    register_quads.append((ontology_uri, URIRef('http://www.w3.org/2000/01/rdf-schema#label'),Literal(label,lang="en")))
                #register_quads.append((ontology_uri, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef('http://www.w3.org/2002/07/owl#Ontology')))
                if description is not None:
                    register_quads.append((ontology_uri, URIRef('http://www.w3.org/2000/01/rdf-schema#comment'), Literal(description,lang="en")))
                
                repo.ds.addN(repo.triples_to_quads(register_quads,  repo.ontology_graph_uri))
                model_triples = list([t for t in g.triples((None, None,None)) if not (repo.detect_bnode(t[2]) or repo.detect_bnode(t[0]))])
                bnode_triples = list([t for t in g.triples((None, None,None)) if (repo.detect_bnode(t[2]) or repo.detect_bnode(t[0]))])
                repo.ds.addN(repo.triples_to_quads(model_triples,ontology_uri.toPython()))
                
                vis = visualise(g.de_skolemize())

            #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                #return str((len(register_quads), len(model_triples), len(bnode_triples)))+str(register_quads)
                return vis
            else:
                return str(len(ont_triples))+str(ont_triples)
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

from flask import send_from_directory




def owl_file_to_graph(owlfile):
    g = Graph()
    g.parse(owlfile,format='xml')
    return g


@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

app.add_url_rule(
    "/uploads/<name>", endpoint="download_file", build_only=True
)

def nav_bar():
    nav_content = render_template_string("""
<table class="_100pc _no_border _bg_white">
    <thead>
        <tr>
            <th><a href="{{url_for('index')}}">Home</a></th>
            <th><a href="{{url_for('view')}}">View</a></th>
            <th><a href="{{url_for('admin')}}">Admin</a></th>
            <th><a href="{{url_for('query')}}">Query</a></th>
            <th><a href="{{url_for('ontologies')}}">Ontologies</a></th>
            <th><a href="{{url_for('upload_file')}}">Visualise</a></th>
            <th><a href="{{url_for('about')}}">About</a></th>
    </thead>
</table>
""")
    return nav_content

@app.route('/about')
def about():
    content = """
    <p><i>OWL models</i> are defined to express domain schemas. Once defined, 
    data in the domains of these models can be uploaded through a convenient flat format 
    which is mapped to the model via a <i>Serialization</i>. A <i>Serialization</i> 
    defines the mappings from the flat file definition to the named objects in the 
    model, along with defining a unique namespaceing scheme aligned to that model to 
    help hierarchically define names and the scopes in which they should be considered 
    unique.</p> 
    
    <p>Once a <i>Serialization</i> is registered into <i>Modelg</i>, data can be
     uploaded from flat files and after <i>mastering</i>, the de-duplicated entities are 
    indexed and packaged as <i>Discourses</i>. 
    A <i>Discourse</i> is a collection of <i>Declarations</i> each of which is associated with and asserts 
    or refutes an individual <i>Posit</i>. A <i>Posit</i> is an atom of 
    information expressed as an RDF <i>triple</i>.
    A <i>Discourse</i> may, instead of referring to a collection of <i>Declarations</i> 
    directly, instead act as a pointer to another <i>Discourse</i>. In this way, recursively, 
    a hierarchy of <i>Discourses</i> can be constructed that enables all the underlying 
    <i>Declarations</i> to be referenced under a single named collection. 
    </p>

    <p>Storage of <i>Posits</i> is indirect. To construct a graph of the <i>Posit</i> contents, 
    their parent <i>Discourse</i> is referenced, and their contents 
    unpacked as a set. Using set logic, the contents of one <i>Discourse</i> can be compared 
    against the contents of another, identifying what's been added, removed or 
    shared across the pair of <i>Discourses</i> under consideration.</p>

    <p><i>Modelg</i> offers a number of visualisations. Some of these are generalised 
    views over RDF, while others are tailored to and coupled with specific model-types.</p>
    """
    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           content=content)


def test_content():
    return  """
    <div class="_90pc">
    <h1>Header 1 Title</h1>
    <p>First paragraph of an article enclosed by &lt;p&gt; tags, 
    this text should be in some font that promotes ease of reading and
    clarity.</p>
    
    <p>A second paragraph should contain text that shares the same 
    font, size and layout properties. In this instance the paragraph 
    is followed by a block-quote:</p>

    <blockquote>Some text sections are presented as blockquotes, 
    these present textual information in a different format 
    altogether, emphasising that they've been sourced from 
    some external publication. </blockquote>

    <p>A third paragraph returns to the normal theme, containing 
    text that shares the same font, size and layout properties. 
    In this instance the paragraph is followed by some 
    un-numbered bullet items.</p>



    <ul>
    <li>List item 1</li>
    <li>Another list item</li>
    <li>A final item on a 3 point list</li>
    </ul>
    </div>
    
    """


def discourse_table_html():
    qr=repo.run_cached_query("get_discourse_details.sparql")
    content_str = "<div width=80%>" + pd.DataFrame(qr).to_html() + "</div>"
    return content_str

# main driver function
if __name__ == "__main__":
    app.run()