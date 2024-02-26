from enum import Enum
import uuid
from PIL import ImageFont
from math import pi, sin, cos, sqrt, atan, atan2, inf

class LocConventions(Enum):
    TOPLEFT=0
    CENTRE=1

def genid():
    return uuid.uuid4().hex

class SVGShape(object):
    """Abstract class for an SVG shape, sets the interface for all shapes defined in this package.
    Objects will all have some kind of text title bar, and a contents panel within which additional content can be displayed.
    Additionally defines some utility functions available at class level for managing geometries and other common operations.

    Common Methods & Attributes
    ------------------------------------------
    id                      - the id of the object
    title                   - title text displayed in the object
    link                    - http link associated with object title
    class_tags              - collection of css class tags associated with the object
    loc                     - (x,y) location of object
    size                    - (w,h) size of object
    orientation             - the angle, or orientation of the object (rotation is considered about object's centre)
    loc_convention          - "centre", or "top-left" - describes the convention the shape uses to interpret x and y locations
    contents                - a collection of objects grouped and located within this shape
    content_layout_method   - a function (from the layouts methods) used to distribute the contents within this shape
    panel_margin            - % the amount of space left free around the shape's panel for use by content layout

    bb_width                - bounding-box width (calculated)
    bb_height               - bounding-box height (calculated)
    bc_radius               - radius of bounding circle (calculated)
    centre_loc              - location of centre of object (calculated)
    top_left_loc            - location of top_left of object (calculated)

    render                  - returns the svg code for the object


    """

    core_kwargs_and_defaults = [('id', genid),
                                ('title', None),
                                ('link', None),
                                ('class_tags', None),
                                ('loc', (0,0)),
                                ('size', (10,10)),
                                ('orientation', 0),
                                ('loc_convention', LocConventions.TOPLEFT),
                                ('contents', None),
                                ('content_layout_method', None),
                                ('panel_margin', 1)
                       ]

    def __init__(self, **kwargs):
        self.apply_kwargs(kwargs, SVGShape.core_kwargs_and_defaults)


    def apply_kwargs(self, kwargs, defaults):
        for k,d in defaults:
            if k in kwargs.keys():
                setattr(self,k, kwargs[k])
            else:
                if callable(d):
                    setattr(self,k, d())
                else:
                    setattr(self,k, d)

    def bb_width(self):
        return self.size[0]

    def bb_height(self):
        return self.size[1]

    def bc_radius(self):
        return SVGShape.distance(self.top_left_loc(), self.centre_loc())

    def centre_loc(self):
        if self.loc_convention == LocConventions.TOPLEFT:
            return (self.loc[0] + (self.size[0]/2), self.loc[1] + (self.size[1]/2))
        elif self.loc_convention == LocConventions.CENTRE:
            return self.loc

    def top_left_loc(self):
        if self.loc_convention is LocConventions.TOPLEFT:
            return self.loc
        elif self.loc_convention is LocConventions.CENTRE:
            return (self.loc[0] - (self.size[0]/2), self.loc[1] - (self.size[1]/2))
        else:
            print (self.loc_convention)

    # Utility geometry functions - all points are (x,y) tuples, and angles in radians
    @staticmethod
    def distance(p1, p2):
    #    x1,y1 = p1
    #    x2,y2 = p2
        dx,dy = SVGShape.dxdy(p1,p2)
        d = sqrt((dx)**2 + (dy)**2)
        return d

    @staticmethod
    def dxdy(p1,p2):
        x1,y1 = p1
        x2,y2 = p2
        return (x2-x1, y2-y1)

    @staticmethod
    def intersection_points_of_two_circles(p1,r1,p2,r2):
        d = SVGShape.distance(p1,p2)
        x1,y1 = p1
        x2,y2 = p2
        if d > (r1+r2):
            return None # No intersection exists
        elif d < abs(r1-r2):
            return None # No intersection - circles are within one another
        elif d==0 and r1 == r2:
            return None # Circules are coincident
        dx,dy = SVGShape.dxdy(p1,p2)
        #dx,dy = (p2[0]-p1[0]),(p2[1]-p1[1])
        a = (r1**2 - r2**2 + d**2)/(2*d)
        h = sqrt(r1**2-a**2)
        px,py = x1 + (dx * a/d), y1 + (dy * a/d)
        rx = -dy * (h/d)
        ry = dx * (h/d)
        ix_points=(px+rx, py+ry), (px-rx, py-ry)
        if ix_points[0]==ix_points[1]:
            ix_points = (px+rx, py+ry)
        return ix_points

    @staticmethod
    def linspace(start, stop, num, endpoint=True):
        if endpoint:
            ep = 1
        else:
            ep = 0
        lrange = stop - start
        interval = (stop - start)/(num-ep)
        return [ start + (interval * e) for e,i in enumerate(range(num))]

    @staticmethod
    def gradient_of_tangent_at_point_on_circle(circle_centre, point):
        dx,dy=SVGShape.dxdy(circle_centre, point)
        if dx != 0:
            g = -dy/dx
        else:
            g = inf
        return g

    @staticmethod
    def gradient_to_radians(g):
        return atan(g)

    @staticmethod
    def angular_bearing(origin, point):
        dy,dx = SVGShape.dxdy(origin, point)
        return atan2(dy,dx)

    @staticmethod
    def point_offset(point, mag, rad):
        dx,dy=sin(rad)*mag, cos(rad)*mag
        return point[0]+dx, point[1]+dy

    @staticmethod
    def get_pil_text_size(text, font_size, font_name):
        font = ImageFont.trutype(font_name, font_size)
        size = font.getsize(text)
        return size
