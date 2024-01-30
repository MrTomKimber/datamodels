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
from rdflib import Graph

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

@app.route('/admin')
def admin():
    content = """admin"""
    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           content=content)

@app.route('/visualise')
def visualise():
    content = """visualise"""
    g = Graph()

    g.parse (MODPATH+'/../src/models/DMEAR/datamodels_rdf.owl', format='xml')
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

    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           content=model_html)


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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('download_file', name=filename))
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
            <th><a href="{{url_for('visualise')}}">Visualise</a></th>
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