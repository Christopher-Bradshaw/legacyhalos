"""
legacyhalos.misc
================

Miscellaneous utility code used by various scripts.

"""
from __future__ import absolute_import, division, print_function

import os, sys
import numpy as np

RADIUS_CLUSTER_KPC = 500.0     # default cluster radius
#SURVEY_DIR = '/global/project/projectdirs/cosmo/data/legacysurvey/dr8'
ZCOLUMN = 'Z_LAMBDA'    

def viewer_inspect(cat):
    """Write a little catalog that can be uploaded to the viewer.

    """
    out = cat['GALAXY', 'RA', 'DEC']
    out.rename_column('GALAXY', 'NAME')
    outfile = os.path.join(os.getenv('HOME'), 'tmp', 'viewer.fits')
    print('Writing {} objects to {}'.format(len(cat), outfile))
    out.write(outfile, overwrite=True)

def imagetool_inspect(cat, group=False):
    """Write a little catalog that can be uploaded to
    https://yymao.github.io/decals-image-list-tool/

    """
    if group:
        galcol, racol, deccol = 'GROUP_NAME', 'GROUP_RA', 'GROUP_DEC'
    else:
        racol, deccol = 'RA', 'DEC'
        galcol = 'GALAXY'
        if not galcol in cat.colnames:
            galcol = 'NAME'
        
    outfile = os.path.join(os.getenv('HOME'), 'tmp', 'inspect.txt')
    print('Writing {} objects to {}'.format(len(cat), outfile))
    with open(outfile, 'w') as ff:
        ff.write('name ra dec\n')
        for ii, (gal, ra, dec) in enumerate(zip(cat[galcol], cat[racol], cat[deccol])):
            if gal.strip() == '':
                if 'ALTNAME' in cat.colnames:
                    gal = cat['ALTNAME'][ii].strip().replace(' ', '')
                    if gal == '':
                        gal = 'galaxy'
                else:
                    gal = 'galaxy'
            ff.write('{} {:.6f} {:.6f}\n'.format(gal, ra, dec))

def srcs2image(cat, wcs, band='r', pixelized_psf=None, psf_sigma=1.0):
    """Build a model image from a Tractor catalog or a list of sources.

    issrcs - if True, then cat is already a list of sources.

    """
    import tractor, legacypipe, astrometry
    from legacypipe.catalog import read_fits_catalog

    if type(wcs) is tractor.wcs.ConstantFitsWcs or type(wcs) is legacypipe.survey.LegacySurveyWcs:
        shape = wcs.wcs.shape
    else:
        shape = wcs.shape
    model = np.zeros(shape)
    invvar = np.ones(shape)

    if pixelized_psf is None:
        vv = psf_sigma**2
        psf = tractor.GaussianMixturePSF(1.0, 0., 0., vv, vv, 0.0)
    else:
        psf = pixelized_psf

    if band == 'FUV':
        _band = 'f'
    elif band == 'NUV':
        _band = 'n'
    else:
        _band = band

    tim = tractor.Image(model, invvar=invvar, wcs=wcs, psf=psf,
                        photocal=tractor.basics.LinearPhotoCal(1.0, band=_band),
                        sky=tractor.sky.ConstantSky(0.0),
                        name='model-{}'.format(band))

    # Do we have a tractor catalog or a list of sources?
    if type(cat) is astrometry.util.fits.tabledata:
        srcs = legacypipe.catalog.read_fits_catalog(cat)
    else:
        srcs = cat

    tr = tractor.Tractor([tim], srcs)
    mod = tr.getModelImage(0)

    return mod

def ellipse_mask(xcen, ycen, semia, semib, phi, x, y):
    """Simple elliptical mask."""
    xp = (x-xcen) * np.cos(phi) + (y-ycen) * np.sin(phi)
    yp = -(x-xcen) * np.sin(phi) + (y-ycen) * np.cos(phi)
    return (xp / semia)**2 + (yp/semib)**2 <= 1

def simple_wcs(onegal, radius=None, factor=1.0, pixscale=0.262, zcolumn='Z'):
    '''Build a simple WCS object for a single galaxy.

    radius in pixels
    '''
    from astrometry.util.util import Tan

    if radius is None:
        if zcolumn in onegal.colnames:
            galdiam = 2 * cutout_radius_kpc(redshift=onegal[zcolumn], pixscale=pixscale)
        else:
            galdiam = 100 # hack! [pixels]
    else:
        galdiam = radius
    
    diam = np.ceil(factor * galdiam).astype('int') # [pixels]
    simplewcs = Tan(onegal['RA'], onegal['DEC'], diam/2+0.5, diam/2+0.5,
                    -pixscale/3600.0, 0.0, 0.0, pixscale/3600.0, 
                    float(diam), float(diam))
    return simplewcs

def ccdwcs(ccd):
    '''Build a simple WCS object for a single CCD table.'''
    from astrometry.util.util import Tan

    W, H = ccd.width, ccd.height
    ccdwcs = Tan(*[float(xx) for xx in [ccd.crval1, ccd.crval2, ccd.crpix1,
                                        ccd.crpix2, ccd.cd1_1, ccd.cd1_2,
                                        ccd.cd2_1, ccd.cd2_2, W, H]])
    return W, H, ccdwcs

def area():
    """Return the area of the DR6+DR7 sample.  See the
    `legacyhalos-sample-selection.ipynb` notebook for this calculation.

    """
    return 6717.906

def cosmology(WMAP=False, Planck=False):
    """Establish the default cosmology for the project."""

    if WMAP:
        from astropy.cosmology import WMAP9 as cosmo
    elif Planck:
        from astropy.cosmology import Planck15 as cosmo
    else:
        from astropy.cosmology import FlatLambdaCDM
        cosmo = FlatLambdaCDM(H0=70, Om0=0.3)        

    return cosmo

def plot_style(font_scale=1.2, paper=False, talk=False):

    import seaborn as sns
    rc = {'font.family': 'serif'}#, 'text.usetex': True}
    #rc = {'font.family': 'serif', 'text.usetex': True,
    #       'text.latex.preamble': r'\boldmath'})
    palette, context = 'Set2', 'talk'
    
    if paper:
        context = 'paper'
        palette = 'deep'
        rc.update({'text.usetex': False})
    
    if talk:
        context = 'talk'
        palette = 'deep'
        rc.update({'text.usetex': True})

    sns.set(context=context, style='ticks', font_scale=font_scale, rc=rc)
    sns.set_palette(palette, 12)

    colors = sns.color_palette()
    #sns.reset_orig()

    return sns, colors

def get_logger(logfile):
    """Instantiate a simple logger.

    """
    import logging
    from contextlib import redirect_stdout

    fmt = "%(levelname)s:%(filename)s:%(lineno)s:%(funcName)s: %(message)s"
    #fmt = '%(levelname)s:%(filename)s:%(lineno)s:%(funcName)s:%(asctime)s: %(message)s']
    datefmt = '%Y-%m-%dT%H:%M:%S'

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # logging to logfile
    ch = logging.FileHandler(logfile, mode='w')
    #ch.setLevel(logging.INFO)
    ch.setFormatter( logging.Formatter(fmt, datefmt=datefmt) )
    logger.addHandler(ch)

    ### log stdout
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.DEBUG)
    #ch.setFormatter( logging.Formatter(fmt, datefmt=datefmt) )
    #logger.addHandler(ch)
    #
    #logger.write = lambda msg: logger.info(msg) if msg != '\n' else None

    return logger

def destroy_logger(log):
    allhndl = list(log.handlers)
    for hndl in allhndl:
        log.removeHandler(hndl)
        hndl.flush()
        hndl.close()

def cutout_radius_kpc(redshift, pixscale=None, radius_kpc=RADIUS_CLUSTER_KPC):
    """Get a cutout radius of RADIUS_KPC [in pixels] at the redshift of the cluster.

    """
    cosmo = cosmology()
    arcsec_per_kpc = cosmo.arcsec_per_kpc_proper(redshift).value
    radius = radius_kpc * arcsec_per_kpc # [float arcsec]
    if pixscale:
        radius = np.rint(radius / pixscale).astype(int) # [integer/rounded pixels]
    return radius

def cutout_radius_cluster(redshift, cluster_radius, pixscale=0.262, factor=1.0,
                          rmin=50, rmax=500, bound=False):
    """Get a cutout radius which depends on the richness radius (in h^-1 Mpc)
    R_LAMBDA of each cluster (times an optional fudge factor).

    Optionally bound the radius to (rmin, rmax).

    """
    cosmo = cosmology()

    radius_kpc = cluster_radius * 1e3 * cosmo.h # cluster radius in kpc
    radius = np.rint(factor * radius_kpc * cosmo.arcsec_per_kpc_proper(redshift).value / pixscale)

    if bound:
        radius[radius < rmin] = rmin
        radius[radius > rmax] = rmax

    return radius # [pixels]

def arcsec2kpc(redshift):
    """Compute and return the scale factor to convert a physical axis in arcseconds
    to kpc.

    """
    cosmo = cosmology()
    return 1 / cosmo.arcsec_per_kpc_proper(redshift).value # [kpc/arcsec]

def statsinbins(xx, yy, binsize=0.1, minpts=10, xmin=None, xmax=None):
    """Compute various statistics in running bins along the x-axis.

    """
    from scipy.stats import binned_statistic

    # Need an exception if there are fewer than three arguments.
    if xmin == None:
        xmin = xx.min()
    if xmax == None:
        xmax = xx.max()

    nbin = int( (np.nanmax(xx) - np.nanmin(xx) ) / binsize )
    stats = np.zeros(nbin, [('xmean', 'f4'), ('xmedian', 'f4'), ('xbin', 'f4'),
                            ('npts', 'i4'), ('ymedian', 'f4'), ('ymean', 'f4'),
                            ('ystd', 'f4'), ('y25', 'f4'), ('y75', 'f4')])

    if False:
        def median(x):
            return np.nanmedian(x)

        def mean(x):
            return np.nanmean(x)

        def std(x):
            return np.nanstd(x)

        def q25(x):
            return np.nanpercentile(x, 25)

        def q75(x):
            return np.nanpercentile(x, 75)

        ystat, bin_edges, _ = binned_statistic(xx, yy, bins=nbin, statistic='median')
        stats['median'] = ystat

        bin_width = (bin_edges[1] - bin_edges[0])
        xmean = bin_edges[1:] - bin_width / 2

        ystat, _, _ = binned_statistic(xx, yy, bins=nbin, statistic='mean')
        stats['mean'] = ystat

        ystat, _, _ = binned_statistic(xx, yy, bins=nbin, statistic=std)
        stats['std'] = ystat

        ystat, _, _ = binned_statistic(xx, yy, bins=nbin, statistic=q25)
        stats['q25'] = ystat

        ystat, _, _ = binned_statistic(xx, yy, bins=nbin, statistic=q75)
        stats['q75'] = ystat

        keep = (np.nonzero( stats['median'] ) * np.isfinite( stats['median'] ))[0]
        xmean = xmean[keep]
        stats = stats[keep]
    else:
        _xbin = np.linspace(xmin, xmax, nbin)
        idx  = np.digitize(xx, _xbin)

        for kk in range(nbin):
            these = idx == kk
            npts = np.count_nonzero( yy[these] )

            stats['xbin'][kk] = _xbin[kk]
            stats['npts'][kk] = npts

            if npts > 0:
                stats['xmedian'][kk] = np.nanmedian( xx[these] )
                stats['xmean'][kk] = np.nanmean( xx[these] )

                stats['ystd'][kk] = np.nanstd( yy[these] )
                stats['ymean'][kk] = np.nanmean( yy[these] )

                qq = np.nanpercentile( yy[these], [25, 50, 75] )
                stats['y25'][kk] = qq[0]
                stats['ymedian'][kk] = qq[1]
                stats['y75'][kk] = qq[2]

        keep = stats['npts'] > minpts
        if np.count_nonzero(keep) == 0:
            return None
        else:
            return stats[keep]

def custom_brickname(ra, dec):
    brickname = '{:06d}{}{:05d}'.format(
        int(1000*ra), 'm' if dec < 0 else 'p',
        int(1000*np.abs(dec)))
    return brickname

def lambda2mhalo(richness, redshift=0.3, Saro=False):
    """
    Convert cluster richness, lambda, to halo mass, given various 
    calibrations.
    
      * Saro et al. 2015: Equation (7) and Table 2 gives M(500).
      * Melchior et al. 2017: Equation (51) and Table 4 gives M(200).
      * Simet et al. 2017: 
    
    Other SDSS-based calibrations: Li et al. 2016; Miyatake et al. 2016; 
    Farahi et al. 2016; Baxter et al. 2016.

    TODO: Return the variance!

    """
    from colossus.halo import mass_defs
    #from colossus.halo import concentration
    
    if Saro:
        pass
    
    # Melchior et al. 2017 (default)
    logM0, Flam, Gz, lam0, z0 = 14.371, 1.12, 0.18, 30.0, 0.5
    M200m = 10**logM0 * (richness / lam0)**Flam * ( (1 + redshift) / (1 + z0) )**Gz

    # Convert to M200c
    #import pdb ; pdb.set_trace()
    #c200m = concentration.concentration(M200m, '200m', redshift, model='bullock01')
    #M200c, _, _ = mass_defs.changeMassDefinition(M200m, c200m, redshift, '200m', '200c')
    #M200c, _, _ = mass_adv.changeMassDefinitionCModel(M200m, redshift, '200m', '200c')

    # Assume a constant concentration.
    M200c = np.zeros_like(M200m)
    for ii, (mm, zz) in enumerate(zip(M200m, redshift)):
        mc, _, _ = mass_defs.changeMassDefinition(mm, 3.5, zz, '200m', '200c')
        M200c[ii] = mc
    
    return np.log10(M200c)

def convert_tractor_e1e2(e1, e2):
    """Convert Tractor epsilon1, epsilon2 values to ellipticity and position angle.

    Taken from tractor.ellipses.EllipseE

    """
    e = np.hypot(e1, e2)
    ba = (1 - e) / (1 + e)
    #e = (ba + 1) / (ba - 1)

    phi = -np.rad2deg(np.arctan2(e2, e1) / 2)
    #angle = np.deg2rad(-2 * phi)
    #e1 = e * np.cos(angle)
    #e2 = e * np.sin(angle)

    return ba, phi

def radec2pix(nside, ra, dec):
    '''Convert `ra`, `dec` to nested pixel number.

    Args:
        nside (int): HEALPix `nside`, ``2**k`` where 0 < k < 30.
        ra (float or array): Right Accention in degrees.
        dec (float or array): Declination in degrees.

    Returns:
        Array of integer pixel numbers using nested numbering scheme.

    Notes:
        This is syntactic sugar around::

            hp.ang2pix(nside, ra, dec, lonlat=True, nest=True)

        but also works with older versions of healpy that didn't have
        `lonlat` yet.
    '''
    import healpy as hp
    theta, phi = np.radians(90-dec), np.radians(ra)
    if np.isnan(np.sum(theta)) :
        raise ValueError("some NaN theta values")

    if np.sum((theta < 0)|(theta > np.pi))>0 :
        raise ValueError("some theta values are outside [0,pi]: {}".format(theta[(theta < 0)|(theta > np.pi)]))

    return hp.ang2pix(nside, theta, phi, nest=True)

def pix2radec(nside, pix):
    '''Convert nested pixel number to `ra`, `dec`.

    Args:
        nside (int): HEALPix `nside`, ``2**k`` where 0 < k < 30.
        ra (float or array): Right Accention in degrees.
        dec (float or array): Declination in degrees.

    Returns:
        Array of RA, Dec coorindates using nested numbering scheme. 

    Notes:
        This is syntactic sugar around::
            hp.pixelfunc.pix2ang(nside, pix, nest=True)
    
    '''
    import healpy as hp

    theta, phi = hp.pixelfunc.pix2ang(nside, pix, nest=True)
    ra, dec = np.degrees(phi), 90-np.degrees(theta)
    
    return ra, dec
    
def pixarea2nside(area):
    """Closest HEALPix nside for a given area.

    Parameters
    ----------
    area : :class:`float`
        area in square degrees.

    Returns
    -------
    :class:`int`
        HEALPix nside that corresponds to passed area.

    Notes
    -----
        - Only considers 2**x nside values (1, 2, 4, 8 etc.)

    """
    import healpy as hp
    
    # ADM loop through nsides until we cross the passed area.
    nside = 1
    while (hp.nside2pixarea(nside, degrees=True) > area):
        nside *= 2

    # ADM there is no nside of 0 so bail if nside is still 1.
    if nside > 1:
        # ADM is the nside with the area that is smaller or larger
        # ADM than the passed area "closest" to the passed area?
        smaller = hp.nside2pixarea(nside, degrees=True)
        larger = hp.nside2pixarea(nside//2, degrees=True)
        if larger/area < area/smaller:
            return nside//2

    return nside

def get_lambdabins(verbose=False):
    """Fixed bins of richness.
    
    nn = 7
    ll = 10**np.linspace(np.log10(5), np.log10(500), nn)
    #ll = np.linspace(5, 500, nn)
    mh = np.log10(lambda2mhalo(ll))
    for ii in range(nn):
        print('{:.3f}, {:.3f}'.format(ll[ii], mh[ii]))    

    """
    # Roughly 13.5, 13.9, 14.2, 14.6, 15, 15.7 Msun
    #lambdabins = np.array([5.0, 10.0, 20.0, 40.0, 80.0, 250.0])

    # Roughly 13.9, 14.2, 14.6, 15, 15.7 Msun
    lambdabins = np.array([10.0, 20.0, 40.0, 80.0, 250.0])
    #lambdabins = np.array([5, 25, 50, 100, 500])
    nlbins = len(lambdabins)
    
    mhalobins = np.log10(lambda2mhalo(lambdabins))

    if verbose:
        for ii in range(nlbins - 1):
            print('Bin {}: lambda={:03d}-{:03d}, Mhalo={:.3f}-{:.3f} Msun'.format(
                ii, lambdabins[ii].astype('int'), lambdabins[ii+1].astype('int'),
                mhalobins[ii], mhalobins[ii+1]))
            
    return lambdabins

def get_zbins(zmin=0.05, zmax=0.35, dt=0.5, verbose=False):
    """Establish redshift bins which are equal in lookback time."""
    import astropy.units as u
    from astropy.cosmology import z_at_value
    
    cosmo = cosmology()
    tmin, tmax = cosmo.lookback_time([zmin, zmax])
    if verbose:
        print('Cosmic time spanned = {:.3f} Gyr'.format(tmax - tmin))
    
    ntbins = np.round( (tmax.value - tmin.value) / dt + 1 ).astype('int')
    #tbins = np.arange(tmin.value, tmax.value, dt) * u.Gyr
    tbins = np.linspace(tmin.value, tmax.value, ntbins) * u.Gyr
    zbins = np.around([z_at_value(cosmo.lookback_time, tt) for tt in tbins], decimals=3)
    tbins = tbins.value
    
    # Now fix the bins:
    # zbins = np.array([0.05, 0.15, 0.25, 0.35, 0.45, 0.6])
    zbins = np.array([0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35])
    #zbins = np.array([0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6])
    tbins = cosmo.lookback_time(zbins).value
    
    if verbose:
        for ii in range(ntbins - 1):
            print('Bin {}: z={:.3f}-{:.3f}, t={:.3f}-{:.3f} Gyr, dt={:.3f} Gyr'.format(
                ii, zbins[ii], zbins[ii+1], tbins[ii], tbins[ii+1], tbins[ii+1]-tbins[ii]))
            
    return zbins

def get_mstarbins(deltam=0.1, satellites=False):
    """Fixed bins of stellar mass.
    
    nn = 7
    ll = 10**np.linspace(np.log10(5), np.log10(500), nn)
    #ll = np.linspace(5, 500, nn)
    mh = np.log10(lambda2mhalo(ll))
    for ii in range(nn):
        print('{:.3f}, {:.3f}'.format(ll[ii], mh[ii]))    
    """

    if satellites:
        pass # code me
    else:
        mstarmin, mstarmax = 9.0, 14.0

    nmstarbins = np.round( (mstarmax - mstarmin) / deltam ).astype('int') + 1
    mstarbins = np.linspace(mstarmin, mstarmax, nmstarbins)
    
    return mstarbins

def missing_files(sample, size=1, filetype='coadds', clobber=False):
    """Find missing data of a given filetype."""    

    if filetype == 'coadds':
        filesuffix = 'image-central.jpg'
    elif filetype == 'ellipse':
        filesuffix = 'ellipsefit.p'
    elif filetype == 'sersic':
        filesuffix = 'sersic-single.p'
    elif filetype == 'sky':
        filesuffix = 'ellipsefit-sky.p'
    else:
        print('Unrecognized file type!')
        raise ValueError

    objdir = '.'
    objid = sample['GALAXY']
    #objid, objdir = legacyhalos.io.get_objid(sample)

    ngal = len(sample)
    indices = np.arange(ngal)
    todo = np.ones(ngal, dtype=bool)
    
    for ii, (objid1, objdir1) in enumerate( zip(np.atleast_1d(objid), np.atleast_1d(objdir)) ):
        residfile = os.path.join(objdir1, '{}-{}'.format(objid1, filesuffix))
        if os.path.exists(residfile) and clobber is False:
            todo[ii] = False

    if np.sum(todo) == 0:
        return list()
    else:
        indices = indices[todo]
    return np.array_split(indices, size)

def missing_coadds(sample, size=1, clobber=False):
    '''Find the galaxies that do not yet have coadds.'''
    return _missing(sample, size=size, filetype='coadds',
                    clobber=clobber)

def missing_ellipse(sample, size=1, clobber=False):
    '''Find the galaxies that do not yet have ellipse fits.'''
    return _missing(sample, size=size, filetype='ellipse',
                    clobber=clobber)

def missing_sersic(sample, size=1, clobber=False):
    '''Find the galaxies that do not yet have Sersic fits.'''
    return _missing(sample, size=size, filetype='sersic',
                    clobber=clobber)

def missing_sky(sample, size=1, clobber=False):
    '''Find the galaxies that do not yet have sky variance estimates.'''
    return _missing(sample, size=size, filetype='sky',
                    clobber=clobber)


def get_area(cen, nside=256, qaplot=False):
    """Get the unique area of the sample.

    """
    import fitsio
    import healpy as hp
    from astropy.table import Table, vstack
    import legacyhalos.io
    
    areaperpix = hp.nside2pixarea(nside, degrees=True)
    samplepix = radec2pix(nside, cen['RA'], cen['DEC'])
    print('Subdividing the sample into nside={} healpixels with area={:.4f} deg2 per pixel.'.format(
        nside, areaperpix))

    outpixmap = []
    for dr, release in zip( ('dr6.0', 'dr7.1'), (6000, 7000) ):
        # Read the pixel weight map which quantifies the imaging footprint
        pixfile = os.path.join( legacyhalos.io.sample_dir(), 'pixweight-{}-0.22.0.fits'.format(dr) )
        pixmap = Table(fitsio.read(pixfile))
        pixmap['DR'] = dr.upper()
    
        these = cen['RELEASE'] == release
        thesepix = np.unique(samplepix[these])
    
        # Only keep non-empty healpixels.
        keep = ( (pixmap['FRACAREA'][thesepix] > 0) * 
                (pixmap['PSFDEPTH_G'][thesepix] > 0) * # p10depth[0]) * 
                (pixmap['PSFDEPTH_R'][thesepix] > 0) * # p10depth[1]) * 
                (pixmap['PSFDEPTH_Z'][thesepix] > 0)   # p10depth[2]) 
               )
        outpixmap.append(pixmap[thesepix][keep])
    outpixmap = vstack(outpixmap)
    
    if False:
        print('Clamping FRACAREA at unity!')
        toobig = outpixmap['FRACAREA'] > 1
        if np.sum(toobig) > 0:
            outpixmap['FRACAREA'][toobig] = 1.0

    # Don't double-count area, where DR6 and DR7 overlap.
    _, keep = np.unique(outpixmap['HPXPIXEL'], return_index=True)
    dup = np.delete( np.arange(len(outpixmap)), keep )
    
    # Code to double-check for duplicates and to ensure every object 
    # has been assigned a healpixel.
    # for pp in outpixmap['HPXPIXEL'][keep]:
    #     if np.sum( pp == outpixmap['HPXPIXEL'][keep] ) > 1:
    #         print('Duplicate!')
    #         import pdb ; pdb.set_trace()
    #     if np.sum( pp == samplepix ) == 0:
    #         print('Missing healpixel!')
    #         import pdb ; pdb.set_trace()
    
    area = np.sum(outpixmap['FRACAREA'][keep]) * areaperpix
    duparea = np.sum(outpixmap['FRACAREA'][dup]) * areaperpix

    if qaplot:
        import matplotlib.pyplot as plt
        uu = np.in1d(samplepix, outpixmap['HPXPIXEL'][keep])
        dd = np.in1d(samplepix, outpixmap['HPXPIXEL'][dup])
        fig, ax = plt.subplots()
        ax.scatter(cen['RA'][uu], cen['DEC'][uu], s=1, marker='s',
                   label=r'Unique: {:.1f} deg$^{{2}}$'.format(area))
        ax.scatter(cen['RA'][dd], cen['DEC'][dd], s=1, marker='s',
                   label=r'Overlapping: {:.1f} deg$^{{2}}$'.format(duparea))
        ax.set_xlim(0, 360)
        ax.set_ylim(-15, 80)
        #ax.legend(loc='upper right', fontsize=12, frameon=False)
        ax.invert_xaxis()
        lgnd = ax.legend(loc='upper left', frameon=False, fontsize=10, ncol=2)
        for ll in lgnd.legendHandles:
            ll._sizes = [30]
        plt.show()
        
    return area, duparea, outpixmap[keep]

def jackknife_samples(cen, pixmap, nside_pixmap=256, nside_jack=4):
    """Split the sample into ~equal area chunks and write out a table.
    
    """
    from astropy.io import fits
    
    area_jack = hp.nside2pixarea(nside_jack, degrees=True)
    area_pixmap = hp.nside2pixarea(nside_pixmap, degrees=True)
    print('Jackknife nside = {} with area = {:.3f} deg2'.format(nside_jack, area_jack))
    
    pix_jack = radec2pix(nside_jack, cen['RA'].data, cen['DEC'].data)
    pix_pixmap = radec2pix(nside_pixmap, cen['RA'].data, cen['DEC'].data)
    
    upix_jack = np.unique(pix_jack)
    upix_jack = upix_jack[np.argsort(upix_jack)]
    npix = len(upix_jack)
    
    ra_jack, dec_jack = pix2radec(nside_jack, upix_jack)
    
    out = Table()
    out['HPXPIXEL'] = upix_jack
    out['RA'] = ra_jack
    out['DEC'] = dec_jack
    out['AREA'] = np.zeros(npix).astype('f4')
    out['NCEN'] = np.zeros(npix).astype('int')
    
    for ii, pp in enumerate(upix_jack):
        these = np.where( pp == pix_jack )[0]
        indx = np.where( np.in1d( pixmap['HPXPIXEL'].data, pix_pixmap[these] ) )[0]
        uindx = np.unique(indx)
        #print(pp, len(indx), len(uindx))

        out['AREA'][ii] = np.sum(pixmap['FRACAREA'][indx].data) * area_pixmap
        out['NCEN'][ii] = len(these)
        
        #if ii == 4:
        #    rbig, dbig = pix2radec(nside_jack, pp)
        #    rsmall, dsmall = pix2radec(nside_pixmap, pixmap['HPXPIXEL'][indx].data)
        #    rgal, dgal = sample['RA'][these], sample['DEC'][these]
        #    plt.scatter(rgal, dgal, s=3, marker='o', color='green')
        #    plt.scatter(rsmall, dsmall, s=3, marker='s', color='blue')
        #    plt.scatter(rbig, dbig, s=75, marker='x', color='k')
        #    plt.show()
        #    import pdb ; pdb.set_trace() 
        
    print('Writing {}'.format(jackfile))
    hx = fits.HDUList()
    hdu = fits.convenience.table_to_hdu(out)
    hdu.header['EXTNAME'] = 'JACKKNIFE'
    hdu.header['NSIDE'] = nside_jack
    hx.append(hdu)
    hx.writeto(jackfile, overwrite=True)

    return out

def ellipse_matrix(r, e1, e2):
    """Calculate transformation matrix from half-light-radius to ellipse

    Parameters
    ----------
    r : :class:`float` or `~numpy.ndarray`
        Half-light radius of the ellipse (ARCSECONDS)
    e1 : :class:`float` or `~numpy.ndarray`
        First ellipticity component of the ellipse
    e2 : :class:`float` or `~numpy.ndarray`
        Second ellipticity component of the ellipse

    Returns
    -------
    :class:`~numpy.ndarray`
        A 2x2 matrix to transform points measured in coordinates of the
        effective-half-light-radius to RA/Dec offset coordinates

    Notes
    -----
        - If a float is passed then the output shape is (2,2,1)
             otherwise it's (2,2,len(r))
        - The parametrization is explained at
             http://legacysurvey.org/dr4/catalogs/
        - Much of the math is taken from:
             https://github.com/dstndstn/tractor/blob/master/tractor/ellipses.py
    """

    # ADM derive the eccentricity from the ellipticity
    # ADM guarding against the option that floats were passed
    e = np.atleast_1d(np.hypot(e1, e2))

    # ADM the position angle in radians and its cos/sin
    theta = np.atleast_1d(np.arctan2(e2, e1) / 2.)
    ct = np.cos(theta)
    st = np.sin(theta)

    # ADM ensure there's a maximum ratio of the semi-major
    # ADM to semi-minor axis, and calculate that ratio
    maxab = 1000.
    ab = np.zeros(len(e))+maxab
    w = np.where(e < 1)
    ab[w] = (1.+e[w])/(1.-e[w])
    w = np.where(ab > maxab)
    ab[w] = maxab

    # ADM convert the half-light radius to degrees
    r_deg = r / 3600.

    # ADM the 2x2 matrix to transform points measured in
    # ADM effective-half-light-radius to RA/Dec offsets
    T = r_deg * np.array([[ct / ab, st], [-st / ab, ct]])

    return T

def is_in_ellipse(ras, decs, RAcen, DECcen, r, e1, e2):
    """Determine whether points lie within an elliptical mask on the sky

    Parameters
    ----------
    ras : :class:`~numpy.ndarray`
        Array of Right Ascensions to test
    decs : :class:`~numpy.ndarray`
        Array of Declinations to test
    RAcen : :class:`float`
        Right Ascension of the center of the ellipse (DEGREES)
    DECcen : :class:`float`
        Declination of the center of the ellipse (DEGREES)
    r : :class:`float`
        Half-light radius of the ellipse (ARCSECONDS)
    e1 : :class:`float`
        First ellipticity component of the ellipse
    e2 : :class:`float`
        Second ellipticity component of the ellipse

    Returns
    -------
    :class:`boolean`
        An array that is the same length as RA/Dec that is True
        for points that are in the mask and False for points that
        are not in the mask

    Notes
    -----
        - The parametrization is explained at
             http://legacysurvey.org/dr4/catalogs/
        - Much of the math is taken from:
             https://github.com/dstndstn/tractor/blob/master/tractor/ellipses.py
    """

    # ADM Retrieve the 2x2 matrix to transform points measured in
    # ADM effective-half-light-radius to RA/Dec offsets...
    G = ellipse_matrix(r, e1, e2)
    # ADM ...and invert it
    Ginv = np.linalg.inv(G[..., 0])

    # ADM remember to correct for the spherical projection in Dec
    # ADM note that this is only true for the small angle approximation
    # ADM but that's OK to < 0.3" for a < 3o diameter galaxy at dec < 60o
    dra = (ras - RAcen)*np.cos(np.radians(decs))
    ddec = decs - DECcen

    # ADM test whether points are larger than the effective
    # ADM circle of radius 1 generated in half-light-radius coordinates
    dx, dy = np.dot(Ginv, [dra, ddec])

    return np.hypot(dx, dy) < 1
