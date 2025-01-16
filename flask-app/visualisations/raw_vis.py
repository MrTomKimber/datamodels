# Test Vis Plugin Template
from visualisations.visualisation import Visualisation
from utils import *
import os, sys
import gravis as gv
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.query import Result
import vis_rdf



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
    widgets.append(gen_graph_dropdown_widget("test_vis_graph"))
    widgets.append(gen_submit_button_widget("test_vis_button", "Go"))
    widgets.append("<hr>")
    return widgets

def gen_widgets_3d():
    widgets = []
    widgets.append("<hr>")
    widgets.append(gen_widget_label_title(plugin_3d.name))
    widgets.append(gen_widget_label_description(plugin_3d.description))
    widgets.append(gen_graph_dropdown_widget("test_vis_3d_graph"))
    widgets.append(gen_submit_button_widget("test_vis_3d_button", "Go"))
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
    gjgf=vis_rdf.process_graph(graph)
    gh=800
    canvas = gv.d3(gjgf,  
        graph_height=gh,
        details_height=300,
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
    return canvas

def gen_vis_3d(graph):
    gjgf=vis_rdf.process_graph(graph)
    gh=600
    canvas = gv.three(gjgf, 
        graph_height=gh,
        node_label_data_source='label',
        show_edge_label=True,
        edge_label_size_factor=0.7,
        edge_label_data_source='label',
        edge_curvature=0.25,
        links_force_strength=0.8, 
        links_force_distance=55,
        many_body_force_strength=-1300,
                    many_body_force_theta=1.61, 
                    use_many_body_force_min_distance=True,
                    many_body_force_min_distance=0.01,
                    use_many_body_force_max_distance=False,
                    many_body_force_max_distance=40000
        ).to_html_partial()
    return canvas


plugin = Visualisation("Raw RDF Visualisation", 
                              "An interactive visualisation of raw rdf data, rolling literal properties into a tabular attachment linked to each node.", 
                              100,
                              "test_vis_button",
                              {"test_vis_graph" : "graphname"},
                              gen_widgets,
                              process_data, 
                              gen_vis 
                              )

plugin_3d = Visualisation("Raw RDF Visualisation in 3D", 
                              "An interactive three-dimensional visualisation of raw rdf data, rolling literal properties into a tabular attachment linked to each node.", 
                              150,
                              "test_vis_3d_button",
                              {"test_vis_3d_graph" : "graphname"},
                              gen_widgets_3d,
                              process_data, 
                              gen_vis_3d 
                              )
