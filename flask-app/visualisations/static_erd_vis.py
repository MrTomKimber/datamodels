# ERD Vis Plugin Template
from visualisations.visualisation import Visualisation
from utils import *
import os, sys
import gravis as gv
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.query import Result
import visualise_erd




def get_sparql(filename):
    with open(os.path.join(sparql_folder,filename)) as sparqlf:
        sparql_text = sparqlf.read()
    return sparql_text

def gen_graph_dropdown_widget(name):
    select_input = """
<select id="{name}" name="{name}">
    {options}
</select>
"""

    g_q = get_sparql("user_graphs.sparql")
    rs2 = repo.run_adhoc_query(g_q)
    option_template="""<option value="{value}">{display}</option>"""
    options=[]
    options.append(option_template.format(value="None",display="---"))
    graph_labels=dict()

    for r in rs2:
        graph_labels[r['g']]=r['label']
        options.append(option_template.format(value=r['g'], display=r['label']))
    options="".join(options)
    return select_input.format(name=name, options=options)

def gen_submit_button_widget(name, display):
    return f"""<input type="submit" id="{name}" name="{name}" value="{display}"/>"""

def gen_widget_label_title(text):
    return "<h3>{text}</h3>".format(text=text)

def gen_widget_label_description(text):
    return "<p>{text}</p>".format(text=text)


def gen_widgets():
    widgets = []
    widgets.append("<hr>")
    widgets.append(gen_widget_label_title(plugin.name))
    widgets.append(gen_widget_label_description(plugin.description))
    widgets.append(gen_graph_dropdown_widget("static_erd_vis_graph"))
    widgets.append(gen_submit_button_widget("static_erd_vis_button", "Go"))
    widgets.append("<hr>")
    return widgets



def process_data(graphname=None):
    q=get_sparql("graph_contents_by_graph.fsparql")
    qr = repo.run_adhoc_query (q.format(graph=graphname), native_rdflib=True)
    g=Graph()
    for row in qr:
        g.add((row['s'], row['p'], row['o']))
    return g

def gen_vis(graph):
    canvas=visualise_erd.generate_static_dot_layout(graph)

    return canvas


plugin = Visualisation("Static Entity Relationship Diagram", 
                              """A static visualisation of a datamodel. <br>
                              Relationships link tables topographically and give 
                              an overview of how a datamodel is structured  
                              with interlinkages shown between key concepts.""", 
                              300,
                              "static_erd_vis_button",
                              {"static_erd_vis_graph" : "graphname"},
                              gen_widgets,
                              process_data, 
                              gen_vis 
                              )

