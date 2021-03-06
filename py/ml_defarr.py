# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import multiprocessing
from scipy import interpolate
from .ml_defang_iter import *
from .ml_counters import *

def ml_defarr(xr, yr, nx, ny, cells, stars, multi=None, bins=1):

    """
    NAME:
      ml_defarr

    PURPOSE:
      Calculate a map of the deflection angle in both the x and y 
      directions as a function of position in the image plane.  The 
      specified y range is broken up into N subgrids (where N=multi) 
      and sent out to N different processors.  Parallel processing 
      can be turned off by setting keyword "multi=False".  The grid 
      is initially coarse but subgridded by a factor of bins in each 
      direction.

    CALLING SEQUENCE:
      defarr = ml_defarr(xr, yr, nx, ny, cells, stars, [multi =, bins= ])

    INPUTS:
      xr    - the x range of the image plane
      yr    - the y range of the image plane
      nx    - the number of coarse pixels in x
      ny    - the number of coarse pixels in y
      cells - multipole moments of star population (list of treecell classes)
      stars - the stellar population (starfield class)

    OPTIONAL INPUTS:
      multi - number of processors to use (default = 4)
      bins  - number of subgrid bins in x and y (default = 1)

    KEYWORDS:

    OUTPUTS:
      defarr - deflection angle map
               (defx = defarr[nx*bins,ny*bins,0]
                defx = defarr[nx*bins,ny*bins,1])

    OPTIONAL OUTPUTS:

    EXAMPLES:

    COMMENTS:

    REVISION HISTORY:
      2013/05/09 - Written by Greg Dobler (KITP/UCSB)

    ------------------------------------------------------------
    """

    # -------- defaults
    multi    = 4 if multi==None else multi


    # -------- utilities
    if multi:
        if ny % multi != 0:
            print("ML_DEFARR: ERROR: Number of image plane y-pixels must be")
            print("ML_DEFARR:  an integer number of processors!!!")
            print("ML_DEFARR:  (i.e., nximg mod multi = 0)")

            return -1

        nproc = multi
        dy    = (yr[1]-yr[0])/float(nproc)
        yrs   = [[i*dy+yr[0],(i+1)*dy+yr[0]] for i in range(nproc)]


    # -------- loop through the image plane
    def run_rect(conn,xr,yr,nx,ny,cells,stars,verbose=False):
        rect = np.zeros([nx,ny,2], dtype=np.float64)
        ximg = np.linspace(xr[0],xr[1],nx,endpoint=False)
        yimg = np.linspace(yr[0],yr[1],ny,endpoint=False)

        for i in range(nx):
            if verbose and ((i+1) % 5 == 0):
                print('ML_DEFARR:     iximg = {0} out ' 
                       'of {1}'.format(i+1, nx), end='\r')
                sys.stdout.flush()

            for j in range(ny):
                rect[i,j,:] = ml_defang_iter(ximg[i],yimg[j],cells,stars)

        if verbose:
            print
            print("ML_DEFARR: Total number of cells used ≈ {0}"
                  .format(counters.cellcnt*nproc))
            print("ML_DEFARR: Total number of stars used ≈ {0}"
                  .format(counters.starcnt*nproc))

        if multi:
            conn.send(rect)
            conn.close()
        else:
            return rect


    # -------- announce the method
    print("ML_DEFARR: looping through the 2D image plane with:")
    print("ML_DEFARR:   multiprocessing      : " + ("ON" if multi  else "OFF"))
    print("ML_DEFARR:   subgrid inerpolation : " + ("ON" if bins>1 else "OFF"))


    # -------- calculate the deflection angle
    if multi:
        print("ML_DEFARR:   running {0} processes...".format(nproc))

        # -------- initialize the deflection array and processes
        defarr  = np.zeros([nx,ny,2], dtype=np.float64)
        parents, childs, ps = [], [], []

        # -------- initialize the pipes and processes, then start
        for ip in range(nproc):
            ptemp, ctemp = multiprocessing.Pipe()
            parents.append(ptemp)
            childs.append(ctemp)
            ps.append(multiprocessing.Process(target=run_rect,
                                              args=(childs[ip],xr,yrs[ip],
                                                    nx,ny//nproc,cells,stars),
                                              kwargs={'verbose':ip==0}))
            ps[ip].start()

        # -------- collect the results, put into defarr, and rejoin
        for ip in range(nproc):
            yind = [ny/nproc*ip,ny/nproc*(ip+1)]
            defarr[0:nx,yind[0]:yind[1],:] = parents[ip].recv()
            ps[ip].join()
    else:
        defarr = run_rect(-314,xr,yr,nx,ny,cells,stars,verbose=True)


    # -------- apply subgrid interpolation if desired
    if bins>1:
        print("ML_DEFARR: applying subgrid spline interpolation " + 
              "with bins = {0}".format(bins))

        # -------- allocate memory
        defarr_fine = np.zeros([nx*bins,ny*bins,2],dtype=np.float64)

        # -------- define coarse and fine grids
        xcoar = np.linspace(xr[0],xr[1],nx,endpoint=False)
        ycoar = np.linspace(yr[0],yr[1],ny,endpoint=False)
        ximg  = np.linspace(xr[0],xr[1],nx*bins,endpoint=False)
        yimg  = np.linspace(yr[0],yr[1],ny*bins,endpoint=False)

        # -------- create the two interpolations
        xm, ym    = np.meshgrid(xcoar,ycoar,indexing='ij')
        coarint_x = interpolate.RectBivariateSpline(xcoar,ycoar,defarr[:,:,0])
        coarint_y = interpolate.RectBivariateSpline(xcoar,ycoar,defarr[:,:,1])

        # -------- run the interpolation
        print("ML_DEFARR:   interpolating alpha_x...")
        defarr_fine[:,:,0] = coarint_x(ximg,yimg)
        print("ML_DEFARR:   interpolating alpha_y...")
        defarr_fine[:,:,1] = coarint_y(ximg,yimg)

        # -------- return the interpolated array
        return defarr_fine
    else:
        return defarr
