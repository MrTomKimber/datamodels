from utils import *

from visualisations.raw_vis import plugin as raw_vis_plugin
from visualisations.erd_vis import plugin as erd_vis_plugin

registered_plugins = [raw_vis_plugin,
                      erd_vis_plugin
                      ]