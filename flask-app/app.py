# Import flask module
from flask import Flask, flash, redirect
from flask import request, render_template_string, render_template, url_for
from flask import send_from_directory, abort
from flask_login import LoginManager, login_required, login_user, UserMixin, current_user
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.encoding import iri_to_uri


from werkzeug.utils import secure_filename
import jinja2


import pandas as pd
import os, sys
import gravis as gv
from rdflib import Graph, URIRef, Literal, BNode
import html
from datetime import datetime

MODPATH=os.path.split(__file__)[0]
sys.path.append(os.path.join(MODPATH,"..","src"))

import repository
import loader
import vis_owl
import vis_rdf

file_loader = jinja2.FileSystemLoader("templates/")
static_folder = jinja2.FileSystemLoader("static/")
sparql_folder = "ui_sparql/"
env = jinja2.Environment(loader=file_loader)
template = env.get_template('page_template.jinja2')

UPLOAD_FOLDER="uploads/"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','rdf','owl','xlsx','csv'}


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

STORETYPE = 'jena'
QUERYENDPOINT="http://fuseki:3030/modelg/query"
UPDATEENDPOINT="http://fuseki:3030/modelg/update"
repo = repository.Repository(store_type=STORETYPE,query_url=QUERYENDPOINT, update_url=UPDATEENDPOINT)

def get_sparql(filename):
    with open(os.path.join(sparql_folder,filename)) as sparqlf:
        sparql_text = sparqlf.read()
    return sparql_text

class User(UserMixin):
    def __init__(self, username):
        self.user_id = username
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    if request.method=="POST":
        # Login and validate the user.
        # user should be an instance of your `User` class
        #login_user(user)
        user=User(request.form.get('username',''))
        login_user(user)
        flash('Logged in successfully.')

        next = request.args.get('next')
        # url_has_allowed_host_and_scheme should check if the url is safe
        # for redirects, meaning it matches the request host.
        # See Django's url_has_allowed_host_and_scheme for an example.
        if not url_has_allowed_host_and_scheme(next, request.host):
            return abort(400)

        return redirect(next or url_for('/'))
    return render_template('login.html', error="error")

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

@app.route('/')
@login_required
def index():
    preamble = """<p>index</p>"""
    control = """"""
    canvas = """"""
    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           preamble=preamble, 
                           control=control,
                           canvas=canvas)


@app.route('/sparql', methods=['GET', 'POST'])
def sparql():
    if request.method == 'POST':
        q = request.form.get('querytext','')
        rs=repo.run_adhoc_query(q)
        rs_tab_html=pd.DataFrame(rs).to_html()
    else:

        q=get_sparql("default_query.sparql")
        rs_tab_html=""

    preamble = """<p>Enter SPARQL query and see results.</p><p><a href="https://sparql.org/query-validator.html" target="_blank" rel="noopener noreferrer">https://sparql.org/query-validator.html</a></p>"""
    control = f"""<form method=post enctype=multipart/form-data method="post">
    <div><textarea name="querytext" id="querytext" rows="10" cols="50" onkeydown="if(event.keyCode===9){{var v=this.value,s=this.selectionStart,e=this.selectionEnd;this.value=v.substring(0, s)+'\t'+v.substring(e);this.selectionStart=this.selectionEnd=s+1;return false;}}">{q}</textarea></div>
    <div><input type=submit value=Query></div></form>"""
    canvas=rs_tab_html

    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           preamble=preamble, 
                           control=control,
                           canvas=canvas)

def _registered_ontologies_control_table():

    q=get_sparql("registered_ontologies.sparql")
    rs=repo.run_adhoc_query(q)
    rs=repository.new_column_to_qr_from_function(rs,
                                      "Visualise",
                                      lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('ont')}" value="Visualise"/>""")
    rs=repository.new_column_to_qr_from_function(rs,
                                    "Delete",
                                    lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('ont')}" value="Delete"/>""")
    rs = repository.reorder_qr_columns(rs, {"Delete":"Delete", "Graph":"g", "Ontology" : "ont", "Label" :"label", "Comment" : "comment", "Triples" : "triples", "Visualise" : "Visualise"})
    rs_tab_html=repository.qr_to_html_table(rs)
    return rs_tab_html

def _registered_serialisations_control_table():
    q=get_sparql("registered_serialisations.sparql")
    rs=repo.run_adhoc_query(q)
    rs=repository.new_column_to_qr_from_function(rs,
                                      "Visualise",
                                      lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('serialisation')}" value="Visualise"/>""")
    rs=repository.new_column_to_qr_from_function(rs,
                                    "Delete",
                                    lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('serialisation')}" value="Delete"/>""")
    rs = repository.reorder_qr_columns(rs, {"Delete": "Delete", "Serialisation":"serialisation", "Name":"label", "Fields" : "mappings", "Visualise" : "Visualise"})
    rs_tab_html=repository.qr_to_html_table(rs)
    return rs_tab_html

def _uploaded_discourses_control_table():

    g_q = get_sparql("user_graphs.sparql")
    rs2 = repo.run_adhoc_query(g_q)
    select_input = """
<select id="{graph}" name="{name}">
    {options}
</select>
"""
    graph_labels=dict()
    option_template="""<option value="{value}">{display}</option>"""
    options=[]
    options.append(option_template.format(value="None",display="---"))
    for r in rs2:
        graph_labels[r['g']]=r['label']
        options.append(option_template.format(value=r['g'], display=r['label']))
    #select_control=select_input.format(options="".join(options))
    options="".join(options)

    q=get_sparql("uploaded_discourses.sparql")
    rs=repo.run_adhoc_query(q)
    rs=repository.new_column_to_qr_from_function(rs,
                                      "Visualise",
                                      lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('discourse')}" value="Visualise"/>""")
    rs=repository.new_column_to_qr_from_function(rs,
                                    "Delete",
                                    lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('discourse')}" value="Delete"/>""")
    rs=repository.new_column_to_qr_from_function(rs,
                                    "Load to Graph",
                                    lambda x : select_input.format(graph=x.get('discourse'),name=x.get('discourse'),options=options) + f"""<input type="submit" id="target" name="target" value="Load to Graph"/>""")

    


    rs = repository.reorder_qr_columns(rs, {"Delete": "Delete", "Discourse":"discourse", "Name":"label", "Declarations" : "declarations", "Visualise" : "Visualise", "Load to Graph" : "Load to Graph"})
    rs_tab_html=repository.qr_to_html_table(rs)
    return rs_tab_html


def _user_graphs_control_table():

    q=get_sparql("user_graphs.sparql")
    rs=repo.run_adhoc_query(q)
    rs=repository.new_column_to_qr_from_function(rs,
                                      "Visualise",
                                      lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('g')}" value="Visualise"/>""")
    rs=repository.new_column_to_qr_from_function(rs,
                                    "Delete",
                                    lambda x : f"""<input type="submit" id="{x.get('g')}" name="{x.get('g')}" value="Delete"/>""")
    rs = repository.reorder_qr_columns(rs, {"Delete": "Delete", "Name":"label", "Graph":"g", "Description": "description", "Triples" : "triples", "Visualise" : "Visualise"})
    rs_tab_html=repository.qr_to_html_table(rs)
    return rs_tab_html



@app.route('/ontologies', methods=['GET', 'POST'])
def ontologies():

    rs_tab_html=_registered_ontologies_control_table()

    preamble = """<p>Show a list of imported ontologies currently hosted by the system and provide the option to visualise them.</p>
    <p>Additionally, provide a link where additional ontologies can be registered by uploading a file in rdf or owl format.</p>"""
    
    control = f"""<form method=post enctype=multipart/form-data method="post">
    <div>{rs_tab_html}</div>
    </form>
    <form action="/upload">
    <div><input type=submit value=Upload></div>
    </form>
    """

    canvas=""""""

    if request.method == 'POST':
        
        request_d = request.form.to_dict()
        
        if "Visualise" in request_d.values():
            o_graph_uri = set([d for d,k in request_d.items() if k=="Visualise"]).pop()
            q=get_sparql("ontologies_by_graph.fsparql").format(o_graph_uri=o_graph_uri)
            g = Graph()
            triples=repo.ds.query( q )
            for t in triples:
                g.add(t)
            canvas=f"""<p>{o_graph_uri}</p>"""+visualise(g.de_skolemize())
        
        elif "Delete" in request_d.values():
            d_graph_uri = set([d for d,k in request_d.items() if k=="Delete"]).pop()
            repo.truncate_graph(d_graph_uri)
            q=get_sparql("delete_ontology_headers.fsparql").format(d_graph_uri=d_graph_uri)
            rs=repo.ds.update(q)

            rs_tab_html=_registered_ontologies_control_table()

            control = f"""<form method=post enctype=multipart/form-data method="post">
            <div>{rs_tab_html}</div>
            </form>
            <form action="/upload">
            <div><input type=submit value=Upload></div>
            </form>
            """

            canvas=""""""

    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           preamble=preamble, 
                           control=control,
                           canvas=canvas)



@app.route('/serialisations', methods=['GET', 'POST'])
def serialisations():

    rs_tab_html=_registered_serialisations_control_table()

    preamble = """<p>Show a list of imported serialisations currently hosted by the system <s>and provide the option to visualise them</s>.</p>
    <p>Additionally, provide a link where additional serialisations can be registered by uploading a file in rdf format.</p>"""
    
    control = f"""<form method=post enctype=multipart/form-data method="post">
    <div>{rs_tab_html}</div>
    </form>
    <form action="/upload_serialisation">
    <div><input type=submit value=Upload></div>
    </form>
    """

    canvas=""""""

    if request.method == 'POST':
        
        request_d = request.form.to_dict()
        
        if "Visualise" in request_d.values():
            o_graph_uri = set([d for d,k in request_d.items() if k=="Visualise"]).pop()
            q = get_sparql("serialisation_contents_by_id.fsparql").format(o_graph_uri=o_graph_uri)
            g = Graph()
            triples=repo.ds.query( q )
            for t in triples:
                g.add(t)
            gjgf=vis_rdf.process_graph(g)

            visual = gv.d3(gjgf, 
                node_label_data_source='label',
                show_edge_label=True,
                edge_label_size_factor=0.7,
                edge_label_data_source='label',
                edge_curvature=0.25,
                links_force_strength=0.8, 
                links_force_distance=55, 
                use_collision_force=True, 
                collision_force_radius=10, 
                collision_force_strength=1.0,
                many_body_force_strength=-1300,
                            many_body_force_theta=1.61, 
                            use_many_body_force_min_distance=True,
                            many_body_force_min_distance=0.01,
                            use_many_body_force_max_distance=False,
                            many_body_force_max_distance=40000,
                            use_x_positioning_force=True,
                            x_positioning_force_strength=0.21,
                            use_y_positioning_force=True,
                            y_positioning_force_strength=0.21
                ).to_html_partial()
            
            canvas=f"""<p>{o_graph_uri}</p>"""+visual
        
        elif "Delete" in request_d.values():
            serialisation_uri = set([d for d,k in request_d.items() if k=="Delete"]).pop()
            q=get_sparql("delete_serialisation_by_id.fsparql").format(serialisation_uri=serialisation_uri)
            rs=repo.ds.update(q)

            rs_tab_html=_registered_serialisations_control_table()

            control = f"""<form enctype=multipart/form-data method="post">
            <div>{rs_tab_html}</div>
            </form>
            <form action="/upload_serialisation">
            <div><input type=submit value=Upload></div>
            </form>
            """

            canvas=""""""

    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           preamble=preamble, 
                           control=control,
                           canvas=canvas)

def dict_strip_nones(dictolists):
    stripped_dict=dict()
    for k,l in dictolists.items():
        if not isinstance(l, list):
            l=[l]
        if not all([v=="None" for v in l]):
            stripped_dict[k]=[v for v in l if v != "None"]
    return stripped_dict



@app.route('/discourses', methods=['GET', 'POST'])
def discourses():
    canvas=""""""
    request_j=""
    t_add=[]
    if request.method=='POST':
    
        request_d = request.form.to_dict()
        request_j = dict_strip_nones(request.form.to_dict(flat=False))
        
        if "Visualise" in request_d.values():
            discourse_e=URIRef(set([d for d,k in request_d.items() if k=="Visualise"]).pop())

            qr = repo.run_cached_query("get_discourse_posits_parms_discourse_iris.sparql", parameters=[discourse_e.n3()], native_rdflib=True)
            g=Graph()
            for row in qr:
                g.add((row['s'], row['p'], row['o']))
            gjgf=vis_rdf.process_graph(g)

            #print(gjgf)

            canvas = gv.d3(gjgf, 
                node_label_data_source='label',
                show_edge_label=True,
                edge_label_size_factor=0.7,
                edge_label_data_source='label',
                edge_curvature=0.25,
                links_force_strength=0.8, 
                links_force_distance=55, 
                use_collision_force=True, 
                collision_force_radius=10, 
                collision_force_strength=1.0,
                many_body_force_strength=-1300,
                            many_body_force_theta=1.61, 
                            use_many_body_force_min_distance=True,
                            many_body_force_min_distance=0.01,
                            use_many_body_force_max_distance=False,
                            many_body_force_max_distance=40000,
                            use_x_positioning_force=True,
                            x_positioning_force_strength=0.21,
                            use_y_positioning_force=True,
                            y_positioning_force_strength=0.21
                ).to_html_partial()


        elif "Delete" in request_d.values():
            discourse_uri = set([d for d,k in request_d.items() if k=="Delete"]).pop()
            q=get_sparql("delete_discourse_detail_by_id.fsparql").format(discourse_uri=discourse_uri)
            rs=repo.ds.update(q)
        
        elif "Load to Graph" in request_d.values():
            # TODO: implement this 
            # for every discourse:graph listed in k,v pairs whose k is not "target",
            # perform an unpacking from that discourse into the target graph.
            
            for k,v in request_d.items():
                if k != "target" and v!="None":
                    discourse_e=URIRef(k)
                    qr = repo.run_cached_query("get_discourse_posits_parms_discourse_iris.sparql", parameters=[discourse_e.n3()], native_rdflib=True)
                    discourse_triples=[]
                    for row in qr:
                        discourse_triples.append((row['s'], row['p'], row['o']))
                    t_add.extend(discourse_triples)
                    t_add.extend(["<br>LOAD<br>",str(discourse_e),k,v,"<br>LOAD<br>"])
                    repo.ds.addN(repo.triples_to_quads(discourse_triples,  URIRef(v)))


            
        

    rs_tab_html=_uploaded_discourses_control_table()

    preamble = """
<p>Show a list of imported discourses currently hosted by the system <s>and provide the option to visualise them</s>.</p>
<p>Discourses contain declarations, but can also reference child discourses allowing merges to be defined. </p>
"""
    
    control = f"""
<form method=post enctype=multipart/form-data method="post">
<div>{rs_tab_html}</div>
</form>
<form action="/upload_discourse">
<div><input type=submit value=Upload></div>
</form>
    """


    return template.render(language_code="en", 
                        title="Modelg", 
                        appname="modelg", 
                        navigation=nav_bar(),
                        preamble=preamble, 
                        control=control,
                        canvas=canvas + str(t_add))



@app.route('/graphs', methods=['GET', 'POST'])
def graphs():
    canvas=""""""
    preamble="""User defined graphs acting as containers for user curated content. """
    default=""

    print(request.form.to_dict())
    if request.method=='POST':
    
        request_d = request.form.to_dict()

        if "Go" in request_d.values(): 
            payload = dict()
            payload['label']=request_d.get("label")
            payload['description']=request_d.get("description")
            repo.generate_user_graph(payload=payload)
        elif "Delete" in request_d.values(): 
            graph_uri = set([d for d,k in request_d.items() if k=="Delete"]).pop()
            q=get_sparql("delete_graph_by_id.fsparql").format(graph_uri=graph_uri)
            rs=repo.ds.update(q)
        elif "Visualise" in request_d.values():
            graph_e=URIRef(set([d for d,k in request_d.items() if k=="Visualise"]).pop())
            q=get_sparql("graph_contents_by_graph.fsparql")
            qr = repo.run_adhoc_query (q.format(graph=graph_e.toPython()), native_rdflib=True)
            g=Graph()
            for row in qr:
                g.add((row['s'], row['p'], row['o']))
            gjgf=vis_rdf.process_graph(g)

            #print(gjgf)

            canvas = gv.d3(gjgf, 
                node_label_data_source='label',
                show_edge_label=True,
                edge_label_size_factor=0.7,
                edge_label_data_source='label',
                edge_curvature=0.25,
                links_force_strength=0.8, 
                links_force_distance=55, 
                use_collision_force=True, 
                collision_force_radius=10, 
                collision_force_strength=1.0,
                many_body_force_strength=-1300,
                            many_body_force_theta=1.61, 
                            use_many_body_force_min_distance=True,
                            many_body_force_min_distance=0.01,
                            use_many_body_force_max_distance=False,
                            many_body_force_max_distance=40000,
                            use_x_positioning_force=True,
                            x_positioning_force_strength=0.21,
                            use_y_positioning_force=True,
                            y_positioning_force_strength=0.21
                ).to_html_partial()

    rs_tab_html=_user_graphs_control_table()
    control=f"""
<form method=post enctype=multipart/form-data method="post">
<div>{rs_tab_html}</div>
</form>

<form enctype="multipart/form-data" method="post">

    <div>
        <label for="label">Label:</label>
        <input type="text" name="label">
    </div>
    <div>
        <label for="description">Description:</label>
        <textarea name="description" id="description" rows="10" cols="50" onkeydown="if(event.keyCode===9){{var v=this.value,s=this.selectionStart,e=this.selectionEnd;this.value=v.substring(0, s)+'\t'+v.substring(e);this.selectionStart=this.selectionEnd=s+1;return false;}}">{default}</textarea>
    </div>


    <input type=submit value="Go" name="Go">
</form>
"""

    return template.render(language_code="en", 
                        title="Modelg", 
                        appname="modelg", 
                        navigation=nav_bar(),
                        preamble=preamble, 
                        control=control,
                        canvas=canvas)
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
            storage_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(storage_filename)
            
            g = owl_file_to_graph(storage_filename).skolemize()     

            
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
    return f'''
<!doctype html>
<title>Upload new File</title>
<h1>Upload new File</h1>
<form method=post enctype=multipart/form-data>
    <input type=file name=file>
    <input type=submit value=Upload>
</form>
'''



@app.route('/upload_serialisation', methods=['GET', 'POST'])
def upload_serialisation_file():
    response = "Nothing yet"
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
            storage_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(storage_filename)
            #g = owl_file_to_graph(file).skolemize()
            response = repo.register_serialization(storage_filename)
    

    return f'''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    <p>{response}
    '''

@app.route('/upload_discourse', methods=['GET', 'POST'])
def upload_discourse_file():
    response = "Nothing yet"
    user = current_user.id
    right_now=datetime.now().strftime("%Y-%m-%dT%H:%M")
    if request.method == 'POST':
        request_d = request.form.to_dict()
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
            storage_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(storage_filename)
            #g = owl_file_to_graph(file).skolemize()
            #response = repo.register_serialization(storage_filename)
            meta_data = {"title" : request_d.get("title"), 
                         "description" : request_d.get("description"), 
                         "createdby" : request_d.get("createdby"), 
                         "createdon" : request_d.get("createdon") 
                         }
            file_data = pd.read_csv(storage_filename, index_col="Sequence")
            datarows = [dict({rk:get_field(rv) for rk, rv in r.items()}) for i,r in file_data.iterrows()]
            col_set = set(repository.get_variables_from_flat_query_results( datarows))
            match_ser=loader.match_serialization_from_columns(repo.ds, repo.registered_serializations_uri,col_set)
            metadata_payload = repo.meta_data_package_template( meta_data )
            result=repo.load_serialization_to_discourse(match_ser, meta_data['title'], metadata_payload, datarows)
            if result is None:
                result = "already loaded?"
            return result




    

    return f'''
    <!doctype html>
    <title>Upload Discourse</title>
    <h1>Upload Discourse</h1>
    <form method=post enctype=multipart/form-data>
    <div>
        <label for="title">Title:</label>
        <input type="text" id="title" name="title"/>
    </div>

    <div>
        <label for="description">Description:</label>
    </div>
    <div>
        <textarea id="description" name="description" cols="40" rows="10" onkeydown="if(event.keyCode===9){{var v=this.value,s=this.selectionStart,e=this.selectionEnd;this.value=v.substring(0, s)+'\t'+v.substring(e);this.selectionStart=this.selectionEnd=s+1;return false;}}"></textarea>
        
    </div>
    

    <div>
        <label for="createdby">Created By:</label>
        <input type="text" id="createdby" name="createdby" value="{user}"/>
    </div>

    <div>
        <label for="created">Created On:</label>
        <input type="datetime-local" id="created" name="created" value="{right_now}"/>
    </div>

    <div>
        <input type="file" name="file"/>
    </div>


      <input type=submit value=Upload/>
    </form>
    '''


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
            <th><a href="{{url_for('sparql')}}">Query</a></th>
            <th><a href="{{url_for('ontologies')}}">Ontologies</a></th>
            <th><a href="{{url_for('serialisations')}}">Serialisations</a></th>
            <th><a href="{{url_for('discourses')}}">Discourses</a></th>
            <th><a href="{{url_for('about')}}">About</a></th>
            <th><a href="{{url_for('graphs')}}">Graphs</a></th>
    </thead>
</table>
""")
    return nav_content

@app.route('/about')
def about():
    preamble = """
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
    control=""
    canvas=""
    return template.render(language_code="en", 
                           title="Modelg", 
                           appname="modelg", 
                           navigation=nav_bar(),
                           preamble=preamble, 
                           control=control,
                           canvas=canvas)


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