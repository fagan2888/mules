from scipy import interpolate
from ml_defang import *
import sys

def ml_defarr(defarr, xr, yr, nx, ny, cells, stars, scheme=None, bins=None):

# -------- defaults
    scheme = 1 if scheme==None else scheme



# -------- scheme 1: loop directly
    if scheme==1:
        print "ML_DEFARR: looping directly through 2D image plane..."

        for iximg in range(nx):
            print 'ML_DEFARR:   iximg = {0} out of {1}\r'.format(iximg+1,nx), 
            sys.stdout.flush()

            for iyimg in range(ny):
                ximg = xr[0] + (xr[1]-xr[0])*float(iximg)/float(nx)
                yimg = yr[0] + (yr[1]-yr[0])*float(iyimg)/float(ny)

                defarr[iximg,iyimg,:] = ml_defang(ximg,yimg,cells,stars,None)

        print
        return

# -------- linearly interpolate in fixed cells
    elif scheme==2:

        # -------- defaults and utilities
        if bins==None: bins = 64
        defur  = np.zeros(2)
        deful  = np.zeros(2)
        deflr  = np.zeros(2)
        defll  = np.zeros(2)
        bp1    = bins + 1                  #
        xind   = np.arange(bp1*bp1) % bp1 #
        yind   = np.arange(bp1*bp1) / bp1 # utilities to be used 
        xfrac  = xind/float(bins)          # for the interpolation
        yfrac  = yind/float(bins)          #
        ncx    = (nx-1)/bins
        ncy    = (ny-1)/bins
        x0, x1 = xr
        y0, y1 = yr
        ddx    = (x1-x0)/float(nx)
        ddy    = (y1-y0)/float(ny)

        print "ML_DEFARR: linearly interpolating 2D img plane with bins= ", \
            bins

        for icx in range(ncx):
            print "ML_DEFARR:   icx = {0} out of {1}\r".format(icx+1,ncx), 
            sys.stdout.flush()

            # -------- get four corners in x
            iximgul = icx*bins
            iximgll = iximgul
            iximgur = iximgul+bins
            iximglr = iximgll+bins

            ximgul = x0 + ddx*float(iximgul)
            ximgur = x0 + ddx*float(iximgur)
            ximgll = x0 + ddx*float(iximgll)
            ximglr = x0 + ddx*float(iximglr)

            for icy in range(ncy):

                # -------- get four corners in y
                iyimgll = icy*bins
                iyimglr = icy*bins
                iyimgul = iyimgll+bins
                iyimgur = iyimglr+bins

                yimgul = y0 + ddy*float(iyimgul)
                yimgur = y0 + ddy*float(iyimgur)
                yimgll = y0 + ddy*float(iyimgll)
                yimglr = y0 + ddy*float(iyimglr)

                # -------- calculate the deflection angles, only need
                #          to do all the corners for special cases
                defur[:] = ml_defang(ximgur, yimgur, cells, stars, None)

                if icx==0:
                    deful[:] = ml_defang(ximgul, yimgul, cells, stars, None)
                else:
                    deful[:] = defarr[iximgul,iyimgul,:]

                if icy==0:
                    deflr[:] = ml_defang(ximglr, yimglr, cells, stars, None)
                else:
                    deflr[:] = defarr[iximglr,iyimglr,:]

                if (icx==0) & (icy==0):
                    defll[:] = ml_defang(ximgll, yimgll, cells, stars, None)
                else:
                    defll[:] = defarr[iximgll,iyimgll,:]


                # -------- bi-linearly interpolate from the four corners
                defarr[xind+iximgll,yind+iyimgll,0] = defll[0]*(1.0-xfrac)* \
                    (1.0-yfrac) + deflr[0]*xfrac*(1.0-yfrac)+ \
                    deful[0]*(1.0-xfrac)*yfrac + defur[0]*xfrac*yfrac
                defarr[xind+iximgll,yind+iyimgll,1] = defll[1]*(1.0-xfrac)* \
                    (1.0-yfrac) + deflr[1]*xfrac*(1.0-yfrac)+ \
                    deful[1]*(1.0-xfrac)*yfrac + defur[1]*xfrac*yfrac

        print
        return

# -------- evaluate grid and then spline
    elif scheme==3:

        print "ML_DEFARR: spline interpolating 2D grid..."

        # -------- defaults and utilities
        if bins==None: bins = 64

        cnx    = nx/bins
        cny    = ny/bins
        coarse = np.zeros([cnx,cny,2])

        for iximg in range(cnx):
            print 'ML_DEFARR:   iximg = {0} out of {1}\r'.format(iximg+1,cnx), 
            sys.stdout.flush()

            for iyimg in range(cny):
                ximg = xr[0] + (xr[1]-xr[0])*float(iximg)/float(cnx)
                yimg = yr[0] + (yr[1]-yr[0])*float(iyimg)/float(cny)

                coarse[iximg,iyimg,:] = ml_defang(ximg,yimg,cells,stars,None)
        print


        # -------- interpolate from the coarse grid onto the real grid
#        xc, yc = np.meshgrid(np.linspace(xr[0],xr[1],cnx), \
#                             np.linspace(yr[0],yr[1],cny))
#        xc, yc = xc.T, yc.T

        xc,yc = np.mgrid[xr[0]:xr[1]:complex(0,cnx),yr[0]:yr[1]:complex(0,cny)]

        #print cnx
        #print cny
        #print xc.dtype
        #print yc.dtype
        #print (coarse[:,:,0]).dtype

        ximg = np.arange(xr[0],xr[1],(xr[1]-xr[0])/float(nx))
        yimg = np.arange(yr[0],yr[1],(yr[1]-yr[0])/float(ny))

        def func(x,y):
#            return (x+y)*np.exp(-5.0*(x**2 + y**2))
            return (x+y)*np.exp(-(x**2 + y**2)/(2*10.**2))

        x,y = np.mgrid[-45:45:10j, -18:18:10j]
        fvals = func(x,y)

        #print ximg.shape, yimg.shape, defarr.shape
        foo = coarse[:,:,0]

        print(fvals.shape)
        print(foo.shape)
        print
        print fvals
        print
        print foo
        import matplotlib.pyplot as plt
        plt.imshow(foo,interpolation='none')
        plt.imshow(fvals,interpolation='none')
        
        newfunc = interpolate.interp2d(x,y,fvals,kind='linear')
        print 'checkpoint 0'

#        defxint = interpolate.interp2d(xc,yc,foo,kind='cubic')
        defxint = interpolate.interp2d(xc,yc,fvals,kind='cubic')
        print 'checkpoint 1'
        defyint = interpolate.interp2d(xc,yc,coarse[:,:,1],kind='cubic')
        print 'checkpoint 2'

        defarr[:,:,0] = defxint(ximg,yimg)
        print 'checkpoint 3'
        defarr[:,:,1] = defyint(ximg,yimg)
        print 'checkpoint 4'

        return

    else:
        print "ML_DEFARR: ONLY SCHEMES #1, 2, and 3 ARE IMPLEMENTED!!!"
        return
