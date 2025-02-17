import networkx as nx
import graphviz
import marshaller

def get_edge_domain_tuple(graph, edge):
    ## requires that the graph nodes be annotated with an attribute called domain.
    fclass = graph.nodes()[edge[0]]
    tclass = graph.nodes()[edge[1]]
    return fclass['domain'], tclass['domain']

def last_common_value(lista, listb):
    for e,i in enumerate(lista):
        if listb[e]!=i:
            return e-1
    return e-1

def popo_to_nx(popo, easy=False):
    g = nx.MultiDiGraph()
    if not easy:
        for c in popo['classes']:
            g.add_node(c.name, **{"name" : c.label, "domain" : c.parent_domain.name})

        for r in popo['relationships']:
            g.add_edge(r.from_class.name, r.to_class.name, relationship=r)
    else:
        for c in popo['classes']:
            g.add_node(c.name, **{"name" : c.label, "domain" : c.parent_domain.name})

        for r in popo['relationships']:
            g.add_edge(r.from_class.name, r.to_class.name)
    return g

def nx_domain_subgraph(popo):
    domain_hierarchy_g=nx_domain_hierarchy_from_dmcar_popo(popo)

    # Create the digraph representing the model
    model_g = popo_to_nx(popo)
    # Note that all the relationships need(?) to be assigned to the lowest level in the hierarchy that covers both sides.

    # Interrogate the available graphs to determine the subgroup clusters attributable to both nodes and edges. 
    rel_domain_interaction_d={}
    domain_relationship_contents_d={}
    for s,f,d in model_g.edges(data=True):
        a = (get_edge_domain_tuple(model_g, (s,f)))
        patha=nx.shortest_path(domain_hierarchy_g, s, "Domain(RootDomain)" )[::-1]
        pathb=nx.shortest_path(domain_hierarchy_g, f, "Domain(RootDomain)" )[::-1]
        lca = domain_hierarchy_g.nodes()[patha[last_common_value(patha, pathb)]]['name']
        # Create a dictionary keyed by relationship name whose values reflect the 
        # lowest common ancestor within the domain hierarchy
        rel_domain_interaction_d[d['relationship'].name]=lca
        if lca not in domain_relationship_contents_d.keys():
            domain_relationship_contents_d[lca]=[d['relationship'].name]
        else:
            domain_relationship_contents_d[lca].append(d['relationship'].name)
            

    return domain_relationship_contents_d

def nx_domain_hierarchy_from_dmcar_popo(popo):
    domain_hierarchy_g = nx.DiGraph()
    for d in popo['domains']:
        domain_hierarchy_g.add_node("Domain("+d.name+")", **{"name" : d.name, "type" : "Domain"})
        
        if isinstance(d.parent_domain, marshaller.Domain):
            domain_hierarchy_g.add_edge("Domain("+d.name+")", "Domain("+d.parent_domain.name+")")
        else:
            domain_hierarchy_g.add_node("Domain(RootDomain)", **{"name" : "RootDomain", "type" : "Domain"})
            domain_hierarchy_g.add_edge("Domain("+d.name+")", "Domain(RootDomain)")

    domain_class_contents_d={}
    for o in popo['classes']:
        domain_hierarchy_g.add_node(o.name, **{"name" : o.name, "type" : "Class"})
        domain_hierarchy_g.add_edge(o.name, "Domain("+o.parent_domain.name+")")
        if o.parent_domain.name not in domain_class_contents_d.keys():
            domain_class_contents_d[o.parent_domain.name]=[o.name]
        else:
            domain_class_contents_d[o.parent_domain.name].append(o.name)

    return domain_hierarchy_g


def recursive_domain_walk_to_graphviz(popo, hierarchy, graph, domain_node, level=0, content=None):
    if content is None:
        #content=graphviz.Digraph(name="Root")
        content=graphviz.Graph(name="Root")

    content_builder = []
    for class_node, data in graph.nodes(data=True):
        if data['domain'] == hierarchy.nodes()[domain_node]['name'] :
            content.node(class_node)
            
    content_builder = []
    for domain in list(hierarchy.reverse().successors(domain_node)):
        with content.subgraph(name="cluster_" + hierarchy.nodes()[domain]['name'] ) as sg:
            recursive_domain_walk_to_graphviz(popo, hierarchy, graph, domain, level+1, sg)

    domain = hierarchy.nodes()[domain_node]['name'] 
    rels_by_domain = nx_domain_subgraph(popo)
    for r in rels_by_domain.get(domain, []):
        for rel_from, rel_to, data in graph.edges(data=True):
            rel = data['relationship']
            
            if rel.name == r:
                print(domain, rel.name)
                content.edge(rel_from, rel_to, label=rel.name)
    
    return content 
            
        