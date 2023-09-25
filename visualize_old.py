import pandas as pd
import pydotplus
from IPython.display import display, Image
from io import StringIO
import pydot
import html

# Utility Functions

def wrapchars(text, t_length=30):
    w_text = []
    li=0
    for i in range(0, len(text), t_length):
        w_text.append(text[li:i])
        li=i
    w_text.append(text[li:])
    return "<BR/>".join(w_text )[5:]

def scorechar(c, loc, target, bchars):
    score=0
    adj=1/target
    neg=0
    if c in bchars:
        if loc>target:
            neg=((loc-target)**3)
        score = 1 / ((( loc-target) **2 ) + 1 + neg)
    else:
        score = 1 / ((( loc-target) **2 ) + 1) *(adj**2)
    return score

def word_wrap(text, target_length):
    linespace = 1.2
    breakchars = " ,.-"
    delchars = "\n\t"
    for c in delchars:
        text = str(text).replace(c," ")
    best_split = 0
    texts = []
    finished=False
    stext = "".join([t for t in text])
    while not finished and len(stext)!=0:
        osp = [scorechar(c,e,target_length, breakchars) for e,c in enumerate(stext)]
        best_split = osp.index(max(osp))

        if len(stext)==0 or best_split==0 or (target_length*linespace)>=len(stext):
            texts.append(stext)
            finished=True
        else:
            texts.append(stext[:best_split+1])
        stext = stext[best_split+1:]
    return texts



# Given a row of data, turn it into a html-like markup row for
# incorporation in an html-like table.
def make_row(att_row, port_name, use_ports=None):

    if use_ports is None:
        use_ports=False

    port = port_name

    contents = dict(att_row)
    row_list=[]
    e=0
    for k,v in contents.items():
        if e == 0:
            if use_ports:
                row_list.append(f"<TD VALIGN=\"TOP\" PORT=\"{port}\"><FONT POINT-SIZE=\"12\">{v}</FONT></TD>")
            else:
                row_list.append(f"<TD VALIGN=\"TOP\" ><FONT POINT-SIZE=\"12\">{v}</FONT></TD>")
        else:
            row_list.append(f"<TD VALIGN=\"TOP\">{v}</TD>")
        e=e+1
    row_content = " ".join(row_list)
    return f"<TR>{row_content}</TR>"


def make_table(ent_df, use_ports=None):

    if use_ports is None:
        use_ports=False

    entity_name = str(ent_df['Entity'].values[0])
    tr_list = []
    for i,r in ent_df[["Attribute"]].iterrows():
        row_form=make_row(r, r['Attribute'], use_ports)
        tr_list.append(f"{row_form}")
    tabular_view=" ".join(tr_list)
    if len(str(ent_df["Entity Description"].values[0]).strip())>0:
        entity_desc=html.escape(str(ent_df["Entity Description"].values[0]).strip())
    else:
        entity_desc=entity_name
    entity_template = f"""{entity_name} [label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2" PORT="{entity_name}" TITLE="{entity_desc}">
        <Th><TD colspan="3" bgcolor="gray"><FONT color="white" POINT-SIZE="18">{entity_name}</FONT></TD></Th>
        <hr></hr>{tabular_view}</TABLE>>, shape=plain, fontname="Helvetica"]"""
    return entity_template

def dot_layout(gname, entities_df, links_df, clusters_df=None, use_ports=None):
    entities=[]
    links=[]

    if use_ports is None:
        use_ports=False

    if clusters_df is None:
        dot_template = """graph V {
        rankdir=UD
        layout=neato
        overlap="false"
        splines="true";

        /* Entities */
        %%entities%%

        /* Links */
        %%links%%
        }"""

        for e in entities_df.groupby("Entity").agg(len).index:
            entities.append(make_table(entities_df.query(f"`Entity`=='{e}'")))

        for i,e in links_df.iterrows():
            if use_ports:
                from_nugget = e['FromClass'] + ":" + e['FromAttribute']
                to_nugget = e['ToClass'] + ":" + e['ToAttribute']
            else:
                from_nugget = e['FromClass']
                to_nugget = e['ToClass']
            links.append( from_nugget + " -- " + to_nugget)

        return dot_template.replace("%%entities%%", "\n".join(entities)).replace("%%links%%", "\n".join(links))
    else:
        dot_template = """graph V {
        rankdir=UD
        layout=fdp
        compound=true
        overlap="false"
        splines="true";

        /* Clusters */
        %%clusters%%

        /* Free Entities */
        %%entities%%

        /* Free Links */
        %%links%%
        }"""

        clust_template = """subgraph %%name%% {
            /* Entities */
            %%entities%%
            /* In-Cluster Links ytb*/

        }"""

        clusters=[]
        link_set=set()
        entity_set=set()
        cluster_mapping = {}
        for i,r in clusters_df.iterrows():
            temp_ents = []
            for ent in r['Entities']:
                temp_ents.append(make_table(entities_df.query(f"`Entity`=='{ent}'")))
                entity_set.add(ent)
                cluster_mapping[ent] = "cluster_"+"_".join([str(q) for q in r['PK']])

            temp_links=[]
            for i,e in links_df.iterrows():
                if e['FromClass'] in set(r['Entities']) and e['ToClass'] in set(r['Entities']):
                    if use_ports:
                        from_nugget = e['FromClass'] + ":" + e['FromAttribute']
                        to_nugget = e['ToClass'] + ":" + e['ToAttribute']
                    else:
                        from_nugget = e['FromClass']
                        to_nugget = e['ToClass']
                    temp_links.append( from_nugget + " -- " + to_nugget)
                    link_set.add( from_nugget + " -- " + to_nugget )
            clusters.append(clust_template.replace("%%name%%","cluster_"+"_".join([str(q) for q in r['PK']])).replace("%%entities%%", "\n".join(temp_ents)).replace("%%links%%", "\n".join(temp_links)) )

        for e in entities_df.groupby("Entity").agg(len).index:
            if e not in entity_set:
                entities.append(make_table(entities_df.query(f"`Entity`=='{e}'")))

        for i,e in links_df.iterrows():

            if e['FromClass'] in cluster_mapping.keys() :
                from_nugget = cluster_mapping[e['FromClass']]
            else:
                if use_ports:
                    from_nugget = e['FromClass'] + ":" + e['FromAttribute']
                else:
                    from_nugget = e['FromClass']

            if e['ToClass'] in cluster_mapping.keys() :
                to_nugget = cluster_mapping[e['ToClass']]
            else:
                if use_ports:
                    to_nugget = e['ToClass'] + ":" + e['ToAttribute']
                else:
                    to_nugget = e['ToClass']

            if from_nugget != to_nugget:
                link_key = from_nugget + " -- " + to_nugget
                if link_key not in link_set:
                    links.append( link_key )
        links=list(set(links))

        return dot_template.replace("%%clusters%%","\n".join(clusters)).replace("%%entities%%", "\n".join(entities)).replace("%%links%%", "\n".join(links))
