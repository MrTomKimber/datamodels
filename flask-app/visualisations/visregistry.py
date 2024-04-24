from utils import *

from visualisations.raw_vis import plugin as raw_vis_plugin
from visualisations.raw_vis import plugin_3d as raw_vis_plugin_3d
from visualisations.erd_vis import plugin as erd_vis_plugin
from visualisations.static_erd_vis import plugin as static_erd_vis_plugin

registered_plugins = [raw_vis_plugin,
                      raw_vis_plugin_3d,
                      erd_vis_plugin, 
                      static_erd_vis_plugin
                      ]