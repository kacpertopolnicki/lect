import pyglet
from pyglet import shapes
import numpy as np

import PIL
from PIL import Image , ImageDraw

import time

from log import logger

ROT90 = np.array([[0.0 , -1.0] , [1.0 , 0.0]] , dtype = np.float64)

# pyglet

def pyglet_circle(x , y , r , geometry = None , shps = None , batch = None , color = None , opacity = None):
    x0 , y0 , x1 , y1 = geometry
    cx = x0 + x * (x1 - x0)
    cy = y0 + y * (x1 - x0)
    rad = r * (x1 - x0)
    c = shapes.Circle(cx , cy , rad , color = color , batch = batch)
    c.opacity = opacity
    shps.append(c)

def pyglet_polygon(*pts , geometry = None , shps = None , batch = None , color = None , opacity = None):
    x0 , y0 , x1 , y1 = geometry
    points = [(x0 + x * (x1 - x0) , y0 + y * (x1 - x0)) for (x , y) in pts]
    p = shapes.Polygon(*points , color = color , batch = batch)
    p.opacity = opacity
    shps.append(p)

def pyglet_multiline(*pts , geometry = None , shps = None , batch = None , color = None , opacity = None):
    x0 , y0 , x1 , y1 = geometry
    points = [(x0 + x * (x1 - x0) , y0 + y * (x1 - x0)) for (x , y) in pts]
    p = shapes.MultiLine(*points , color = color , batch = batch)
    p.opacity = opacity
    shps.append(p)

def pyglet_draw_shapes(shapes_list , paperGeometry ,
                shps = None , batch = None):
    for s in shapes_list:
        fun = s["type"]
        if fun == "circle":
            shape = pyglet_circle(*s["center"] , *[s["radius"]] , 
                           color = s["color"] , 
                           opacity = s["opacity"] ,
                           geometry = paperGeometry , batch = batch , shps = shps)
        elif fun == "polygon":
            shape = pyglet_polygon(*s["points"] , 
                           color = s["color"] , 
                           opacity = s["opacity"] ,
                           geometry = paperGeometry , batch = batch , shps = shps)
        elif fun == "multiline":
            shape = pyglet_multiline(*s["points"] , 
                           color = s["color"] , 
                           opacity = s["opacity"] ,
                           geometry = paperGeometry , batch = batch , shps = shps)

# pil

def pil_circle(draw , x , y , r , geometry = None , color = None , opacity = None):
    x0 , y0 , x1 , y1 = geometry
    cx = x0 + x * (x1 - x0)
    cy = y1 - y * (x1 - x0)
    rad = r * (x1 - x0)
    r , b , g  = color
    a = opacity
    draw.circle((cx , cy) , rad , fill = (r , b , g , a) , outline = (0 , 0 , 0 , 0) , width = 0)

def pil_polygon(draw , *pts , geometry = None , color = None , opacity = None):
    x0 , y0 , x1 , y1 = geometry
    points = [(x0 + x * (x1 - x0) , y1 - y * (x1 - x0)) for (x , y) in pts]
    r , b , g = color
    a = opacity
    draw.polygon(points , fill = (r , b , g , a) , outline = (0 , 0 , 0 , 0) , width = 0)

def pil_draw_shapes(draw , shapes_list , paperGeometry):
    for s in shapes_list:
        fun = s["type"]
        if fun == "circle":
            shape = pil_circle(draw , *s["center"] , *[s["radius"]] , 
                           color = s["color"] , 
                           opacity = s["opacity"] ,
                           geometry = paperGeometry)
        elif fun == "polygon":
            shape = pil_polygon(draw , *s["points"] , 
                           color = s["color"] , 
                           opacity = s["opacity"] ,
                           geometry = paperGeometry)
# for drawing strokes

def simple_stroke_shapes(pts , parameters = None):

    if len(pts) < 2:
        return []

    thickness = 0.005
    color = (255 , 255 , 255)
    opacity = 255
    if parameters is not None:
        thickness = parameters["thickness"]
        color = parameters["color"]
        opacity = parameters["opacity"]

    ptsnp = np.array(pts , dtype = np.float64)

    coord = ptsnp[: , :2]
    press = ptsnp[: , 2]

    # normalized vectors along segment
    nvect = np.roll(coord , -1 , axis = 0) - coord 
    nvect = nvect / np.linalg.norm(nvect , axis = 1)[: , None] # todo, the last value is problematic

    # normalized vectors perpendicular to segment
    pvect = np.matmul(ROT90 , nvect.T).T

    # radius
    rad = press * thickness

    # polygon todo
    poly1 = coord + pvect * rad[: , None]
    poly2 = coord - pvect * rad[: , None]

    allshapes = []

    for j in range(len(ptsnp) - 1):
        c1x , c1y = float(coord[j , 0]) , float(coord[j , 1])
        rad1 = float(rad[j])
        c2x , c2y = float(coord[j + 1 , 0]) , float(coord[j + 1 , 1])
        rad2 = float(rad[j + 1])
       
        circle1 = {"type" : "circle" , "center" : (c1x , c1y) , "radius" : rad1 , "color" : color , "opacity" : opacity}
        circle2 = {"type" : "circle" , "center" : (c2x , c2y) , "radius" : rad2 , "color" : color , "opacity" : opacity}
        
        p1x , p1y = float(
                            (coord[j , 0] + pvect[j , 0] * rad[j]) 
                    ) , float(
                            (coord[j , 1] + pvect[j , 1] * rad[j]) 
                    )
        p2x , p2y = float(
                            (coord[j , 0] - pvect[j , 0] * rad[j]) 
                    ) , float(
                            (coord[j , 1] - pvect[j , 1] * rad[j]) 
                    )
        p3x , p3y = float(
                            (coord[j + 1 , 0] - pvect[j , 0] * rad[j + 1]) 
                    ) , float(
                            (coord[j + 1 , 1] - pvect[j , 1] * rad[j + 1]) 
                    )
        p4x , p4y = float(
                            (coord[j + 1 , 0] + pvect[j , 0] * rad[j + 1]) 
                    ) , float(
                            (coord[j + 1 , 1] + pvect[j , 1] * rad[j + 1]) 
                    )

        poly = {"type" : "polygon" , "points" : ((p1x , p1y) , (p2x , p2y) , (p3x , p3y) , (p4x , p4y)) , "color" : color , "opacity" : opacity}

        allshapes.append(circle1)
        allshapes.append(circle2)
        allshapes.append(poly)
        
    return allshapes

def multiline_stroke_shapes(pts , parameters = None):

    thickness = 0.01
    color = (255 , 255 , 255)
    opacity = 255
    if parameters is not None:
        thickness = parameters["thickness"]
        color = parameters["color"]
        opacity = parameters["opacity"]

    ptsnp = np.array(pts , dtype = np.float64)

    coord = ptsnp[: , :2]
    press = ptsnp[: , 2]

    poly = {
            "type" : "multiline" , 
            "points" : coord.tolist() , 
            "color" : color , 
            "opacity" : opacity}
        
    return [poly]
