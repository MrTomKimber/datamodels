import sys,os
import importlib
import glob

class Visualisation(object):
    def __init__(self, 
                 name, 
                 description, 
                 priority, 
                 trigger,
                 parameters, 
                 gen_widgets_function, 
                 prep_data_function, 
                 gen_html_function):
        
        self.name = name
        self.description = description
        self.priority = priority
        self.trigger = trigger
        self.parameters = parameters
        self.gen_widgets_function = gen_widgets_function
        self.prep_data_function = prep_data_function
        self.gen_html_function = gen_html_function
    
    def _map_parameters(self, response_dict):
        pmap = {}
        for k,v in self.parameters.items():
            if k in response_dict:
                pmap[v]=response_dict[k]
        return pmap


    def _get_data(self, context_parameters):
        parameters = self._map_parameters(context_parameters)
        return self.prep_data_function(**parameters)
    
    def _gen_html(self, rdflib_graph):
        return self.gen_html_function(rdflib_graph)
    
    def _gen_widgets(self):
        return self.gen_widgets_function()
    
