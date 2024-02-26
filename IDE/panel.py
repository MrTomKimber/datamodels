from shape import SVGShape

class Panel(SVGShape):
    """Panel shape, rectangular, with optional curved corners.
    The panel has an optional title bar-running along its top,
    and an internal rectangular section that provides a canvas
    for additional content to be rendered internally. """

    kwargs_and_defaults = [ ('corner_radius_ratio', 0.1),
                            ('title_panel_ratio', 0.15),
                            ('aspect_ratio', 1.0)
                            ]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_kwargs(kwargs, Panel.kwargs_and_defaults)

    def _title_path_steps(self):
        rad = self.corner_radius_ratio
        p_defs = []
        width, height = self.size[0],self.size[1] * self.title_panel_ratio
        line_specs = ["M {p6x} {p6y} ",
                "L {p1x} {p1y} " ,
                "Q {cp1x} {cp1y} {p2x} {p2y} " ,
                "L {p3x} {p3y}",
                "Q {cp2x} {cp2y} {p4x} {p4y} ",
                "L {p5x} {p5y} ",
                ]
                # ]

        line = ""
        x,y = self.loc
        p1x,p1y = x, y+self.corner_radius_ratio
        cp1x,cp1y = x, y
        p2x,p2y = x+self.corner_radius_ratio, y
        p3x,p3y = x+width-self.corner_radius_ratio, y
        cp2x,cp2y = x+width, y
        p4x,p4y = x+width, y+self.corner_radius_ratio
        p5x,p5y = x+width, y+height
        p6x,p6y = x, y+height
        point_defs = {  "p1x" : p1x,
                        "p1y" : p1y,
                        "cp1x" : cp1x,
                        "cp1y" : cp1y,
                        "p2x" : p2x,
                        "p2y" : p2y,
                        "p3x" : p3x,
                        "p3y" : p3y,
                        "cp2x" : cp2x,
                        "cp2y" : cp2y,
                        "p4x" : p4x,
                        "p4y" : p4y,
                        "p5x" : p5x,
                        "p5y" : p5y,
                        "p6x" : p6x,
                        "p6y" : p6y }
        for l in line_specs:
            p_defs.append(l.format(**point_defs))
        return p_defs

    def _panel_path_steps(self):
        rad = self.corner_radius_ratio
        p_defs = []
        title_height = self.size[1] * self.title_panel_ratio
        width, height = self.size[0],self.size[1] * (1-self.title_panel_ratio)
        #line_specs = ["M {p1x} {p1y} " ,
        line_specs = ["M {p2x} {p2y} " ,
#                "L {p2x} {p2y}",
                "L {p3x} {p3y}",
                "Q {cp1x} {cp1y} {p4x} {p4y} " ,
                "L {p5x} {p5y}",
                "Q {cp2x} {cp2y} {p6x} {p6y}",
                "L {p1x} {p1y} "
                 ]

        line = ""
        x,y = self.loc
        p1x,p1y = x, y+title_height
        p2x,p2y = x+width, y+title_height
        p3x,p3y = x+width, y+title_height+height-self.corner_radius_ratio
        cp1x,cp1y = x+width, y+title_height+height
        p4x,p4y = x+width-self.corner_radius_ratio, y+title_height+height
        p5x,p5y = x+self.corner_radius_ratio, y+title_height+height
        cp2x,cp2y = x, y+title_height+height
        p6x,p6y = x, y+title_height+height-self.corner_radius_ratio

        point_defs = {  "p1x" : p1x,
                        "p1y" : p1y,
                        "cp1x" : cp1x,
                        "cp1y" : cp1y,
                        "p2x" : p2x,
                        "p2y" : p2y,
                        "p3x" : p3x,
                        "p3y" : p3y,
                        "cp2x" : cp2x,
                        "cp2y" : cp2y,
                        "p4x" : p4x,
                        "p4y" : p4y,
                        "p5x" : p5x,
                        "p5y" : p5y,
                        "p6x" : p6x,
                        "p6y" : p6y }
        for l in line_specs:
            p_defs.append(l.format(**point_defs))
        return p_defs
