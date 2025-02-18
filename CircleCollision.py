# -*- coding: utf-8 -*-
"""
Created on Wed Apr 10 22:41:18 2019

@author: Vosburgh
"""

import numpy
import os
import pycuda.autoinit
import pycuda.driver as drv
import random
import time

from pycuda.compiler import SourceModule
import pycuda.gpuarray as gpuarray
from Shapes import Circle

#if on windows, try to find cl.exe
if os.name=='nt':
    if (os.system("cl.exe")):
        os.environ['PATH'] += ';'+r"C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\amd64"
        if (os.system("cl.exe")):
            raise RuntimeError("cl.exe still not found, path probably incorrect")

def generateRandomCircles(numCircles, x_range = range(1,400), \
        y_range = range(1,400), radius_range = range(5,30)):
    random.seed()
    x = [random.choice(x_range) for i in range(numCircles)]
    y = [random.choice(y_range) for i in range(numCircles)]
    rad = [random.choice(radius_range) for i in range(numCircles)]
    circles = [Circle(x[i],y[i],rad[i]) for i in range(numCircles)]
    return circles

def detectCollisionGPU(robot, obstacles):
    #print("compiling kernel")
    mod = SourceModule("""
    __global__ void check_collisions(
        float x_robot, float y_robot, float r_robot,
        float *x_obs, float *y_obs, float *r_obs, 
        bool *collisions)
    {
        int obstacleId = threadIdx.x;
        float distance = hypotf(x_robot - x_obs[obstacleId], y_robot - y_obs[obstacleId]);
        collisions[obstacleId] = (distance <= r_robot + r_obs[obstacleId] );
    }
    """)
    #print("compiled kernel")

    
    check_collisions = mod.get_function("check_collisions")
    
    
    #constants that will be passed directly to kernel
    x_robot = robot.x
    y_robot = robot.y
    r_robot = robot.rad

    #allocating arrays on the gpu for obstacle coordinates and radii
    x_obs_gpu = gpuarray.to_gpu(numpy.asarray([circle.x for circle in obstacles]))#nVidia only supports single precision)
    y_obs_gpu = gpuarray.to_gpu(numpy.asarray([circle.y for circle in obstacles]))
    r_obs_gpu = gpuarray.to_gpu(numpy.asarray([circle.rad for circle in obstacles]))

    collisions = numpy.zeros(len(obstacles), dtype=bool)
    gpuStart = time.time()
    check_collisions(
            x_robot, y_robot, r_robot,
            x_obs_gpu, y_obs_gpu, r_obs_gpu,
            drv.InOut(collisions),
            block=(len(obstacles),1,1), grid=(1,1))
    duration = time.time()-gpuStart
    #print("gpu time taken = "+str(time.time()-gpuStart))
    #print(collisions)

    return collisions, duration

def detectCollisionCPU(robot, obstacles):
    cpuStart = time.time()
    collisions = [False]*len(obstacles)
    i = 0
    x_robot = robot.x
    y_robot = robot.y
    r_robot = robot.rad
    while i < len(obstacles):
        obs = obstacles[i]
        distance = numpy.sqrt((x_robot-obs.x)**2 + (y_robot-obs.y)**2)
        collisions[i]= (distance <= r_robot + obs.rad)
        i=i+1
    duration = time.time()-cpuStart
    #print("cpu time taken = "+str(time.time()-cpuStart))
    #print(collisions)
    return collisions, duration