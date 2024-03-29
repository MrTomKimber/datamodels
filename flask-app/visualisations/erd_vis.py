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
    widgets.append(gen_graph_dropdown_widget("erd_vis_graph"))
    widgets.append(gen_submit_button_widget("erd_vis_button", "Go"))
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
    gjgf=visualise_erd.process_graph(graph)
    canvas = gv.d3(gjgf, 
                    layout_algorithm_active=True, 
                    node_label_data_source='label',
                    show_edge_label=True,
                    edge_label_size_factor=1.0,
                    edge_label_data_source='label',
                    node_image_size_factor=5,
                    node_size_factor=0.20,
                    show_node_label=False,
                    edge_curvature=0.25,
                    links_force_strength=0.65, 
                    links_force_distance=80, 
                    use_collision_force=True, 
                    collision_force_radius=30, 
                    collision_force_strength=30.0,
                    many_body_force_strength=-1300,
                    many_body_force_theta=0.56, 
                    use_many_body_force_min_distance=False,
                    many_body_force_min_distance=0.01,
                    use_many_body_force_max_distance=False,
                    many_body_force_max_distance=40000,
                    use_x_positioning_force=False,
                    x_positioning_force_strength=0.21,
                    use_y_positioning_force=False,
                    y_positioning_force_strength=0.21
     ).to_html_partial()
    return canvas


plugin = Visualisation("Entity Relationship Diagram", 
                              "An interactive visualisation of a datamodel. <br> Relationships link tables topographically and can give a quick overview of how a datamodel is constructed with interlinkages shown between key concepts.", 
                              200,
                              "erd_vis_button",
                              {"erd_vis_graph" : "graphname"},
                              gen_widgets,
                              process_data, 
                              gen_vis 
                              )

