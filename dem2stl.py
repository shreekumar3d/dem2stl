#!/usr/bin/env python3
from PIL import Image
from stl import mesh
import numpy
import sys

# FIXME: parameterize this later

img = Image.open(sys.argv[1])
w, h = img.size
print('DEM Size = ',w,h) # Test file is 2447 3414 => 73.41 km x 102.42
faces = []

factor = 4 # 1:factor*50k is the scale
x_size = 333*factor
y_size = 333*factor
print('DEM Clip = ', x_size, y_size)

x_start = w-x_size-1 # right align
y_start = 0 # h-y_size-1 # if you want to bottom align

## skip undefined (0) region on the right side
## ideally, these things must be passed as args to the script
#x_start -= 183
#y_start += 9

x_end = x_start + x_size - 1
y_end = y_start + y_size - 1

# 30 m per topo point
# 1:50000 scale means 1 meter is 50 km => 20 cm is 10 km
# 1:100000 scale means 1 meter is 100 km => 20 cm is 20 km
# 1:250000 scale means 1 meter is 250 km => 20 cm is 50 km
#
# Top map has to keep things even, we actually use do 19.98 cm
point_scale = 30 # distance between adjacent points, in meters
topo_scale = factor*50*1000
x_scale = (point_scale*1000)/topo_scale
y_scale = (point_scale*1000)/topo_scale

base_alt = 9999
null_alts = 0
for x in range(x_start,x_start+x_size+1):
    for y in range(y_start,y_start+y_size+1):
        height = img.getpixel((x,y))
        if height != 0:
            base_alt = min(height, base_alt)
        else:
            null_alts += 1
base_alt = ((base_alt)//500)*500
print('Base altitude for DEM = %d m'%(base_alt))
print('Number of DEM points where altitude is ZERO meters = %d %s'%(null_alts, '(good)' if (null_alts==0) else "(why?)"))

def to_alt(x):
    alt = max(x-base_alt,0)
    return (alt*2)/100

# Iterate over grid of interest,
# spit two triangles per iteration
#
# Grid below is
# p0,p1
# p3 p2
#
# Special case is the edges, where we
# need extra triangles going all the way
# to z=0
maxalt = 0
minalt = 9999
for x in range(x_start,x_start+x_size):
    for y in range(y_start,y_start+y_size):
        x0 = x_scale*(x-x_start)
        x1 = x_scale*((x-x_start)+1)
        x2 = x_scale*((x-x_start)+1)
        x3 = x_scale*(x-x_start)

        y0 = y_scale*(y-y_start)
        y1 = y_scale*(y-y_start)
        y2 = y_scale*((y-y_start)+1)
        y3 = y_scale*((y-y_start)+1)

        height0 = img.getpixel((x,y))
        height1 = img.getpixel((x+1,y))
        height2 = img.getpixel((x+1,y+1))
        height3 = img.getpixel((x,y+1))

        maxalt = max(height0, height1, height2, height3, maxalt)
        if height0 != 0:
            minalt = min(height0, minalt)
        if height1 != 0:
            minalt = min(height1, minalt)
        if height2 != 0:
            minalt = min(height2, minalt)
        if height3 != 0:
            minalt = min(height3, minalt)

        height0 = to_alt(height0)
        height1 = to_alt(height1)
        height2 = to_alt(height2)
        height3 = to_alt(height3)

        #height0 = y0
        #height1 = y1
        #height2 = y2
        #height3 = y3

        y0 = -y0
        y1 = -y1
        y2 = -y2
        y3 = -y3

        face012 = numpy.array([[x0,y0,height0],
                              [x1,y1,height1],
                              [x2,y2,height2]])
        face023 = numpy.array([[x0,y0,height0],
                              [x2,y2,height2],
                              [x3,y3,height3]])
        faces.append(face012)
        faces.append(face023)

        if x == x_start:
            faces.append(numpy.array([[x0, y0, 0],
                                      [x0, y0, height0],
                                      [x3, y3, height3]]))
            faces.append(numpy.array([[x0, y0, 0],
                                      [x3, y3, height3],
                                      [x3, y3, 0]]))
        if x == x_end:
            faces.append(numpy.array([[x1, y1, 0],
                                      [x2, y2, height2],
                                      [x1, y1, height1]]))
            faces.append(numpy.array([[x1, y1, 0],
                                      [x2, y2, 0],
                                      [x2, y2, height2]]))
        if y == y_start:
            faces.append(numpy.array([[x0, y0, 0],
                                      [x1, y1, 0],
                                      [x0, y0, height0]]))
            faces.append(numpy.array([[x1, y1, 0],
                                      [x1, y1, height1],
                                      [x0, y0, height0]]))
        if y == y_end:
            faces.append(numpy.array([[x3, y3, 0],
                                      [x3, y3, height3],
                                      [x2, y2, height2]]))
            faces.append(numpy.array([[x3, y3, 0],
                                      [x2, y2, height2],
                                      [x2, y2, 0]]))

x0 = 0
x1 = x_scale*x_size
x2 = x_scale*x_size
x3 = 0

y0 = 0
y1 = 0
y2 = y_scale*y_size
y3 = y_scale*y_size
# Add bottom face so that this is a tight mesh by itself
# Actually speaking this is not perfect, we need triangles
# or quads to achieve a tight mesh with floating point data.
# That said, the slicer takes care of this, so being a bit
# lazy isn't bad. We could output two triangles per iteration
# in the main loop, but then we'd have 2x the triangles,
# so slower slicing.
faces.append(numpy.array([[x0, y0, 0],
                          [x1, -y1, 0],
                          [x2, -y2, 0]]))
faces.append(numpy.array([[x0, -y0, 0],
                          [x2, -y2, 0],
                          [x3, -y3, 0]]))
print('DEM Max Alt = %d m Min alt = %d m'%(maxalt, minalt))
print('DEM triangles =',len(faces))
data = numpy.zeros(len(faces), dtype=mesh.Mesh.dtype)
for i in range(len(faces)):
    data['vectors'][i] = faces[i]

dem = mesh.Mesh(data)

# Add the base mesh, which shows the base elevation
markup_mesh = mesh.Mesh.from_file('templates/base-%d.stl'%(base_alt))
#markup_mesh.vectors *= 10 # if you want to scale 10x
combined = mesh.Mesh(numpy.concatenate([dem.data, markup_mesh.data]))

# Write out the DEM+base
out_fname = 'test.stl'
combined.save(out_fname)
print('Output File=%s Scale = 1:%d'%(out_fname, factor*50000))
