"""
legacyhalos.misc
================

Miscellaneous utility code used by various scripts.

"""
from __future__ import absolute_import, division, print_function

import sys
import numpy as np

def legacyhalos_cosmology(WMAP=False, Planck=False):
    """Establish the default cosmology for the project."""

    if WMAP:
        from astropy.cosmology import WMAP9 as cosmo
    elif Planck:
        from astropy.cosmology import Planck15 as cosmo
    else:
        from astropy.cosmology import FlatLambdaCDM
        cosmo = FlatLambdaCDM(H0=70, Om0=0.3)        

    return cosmo

def legacyhalos_plot_style(paper=False, talk=False):

    import seaborn as sns
    rc = {'font.family': 'serif'}#, 'text.usetex': True}
    #rc = {'font.family': 'serif', 'text.usetex': True,
    #       'text.latex.preamble': r'\boldmath'})
    palette = 'Set2'
    
    if paper:
        palette = 'deep'
        rc.update({'text.usetex': False})
    
    if talk:
        pass

    sns.set(style='ticks', font_scale=1.6, rc=rc)
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

def cutout_radius_150kpc(redshift, pixscale=0.262, radius_kpc=150):
    """Get a cutout radius of 150 kpc [in pixels] at the redshift of the cluster.

    """
    cosmo = legacyhalos_cosmology()
    arcsec_per_kpc = cosmo.arcsec_per_kpc_proper(redshift).value
    radius = np.rint(radius_kpc * arcsec_per_kpc / pixscale).astype(int) # [pixels]
    return radius

def cutout_radius_cluster(redshift, cluster_radius, pixscale=0.262, factor=1.0,
                          rmin=50, rmax=500, bound=False):
    """Get a cutout radius which depends on the richness radius (in h^-1 Mpc)
    R_LAMBDA of each cluster (times an optional fudge factor).

    Optionally bound the radius to (rmin, rmax).

    """
    cosmo = legacyhalos_cosmology()

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
    cosmo = legacyhalos_cosmology()
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

def custom_brickname(ra, dec, prefix='custom-'):
    brickname = 'custom-{:06d}{}{:05d}'.format(
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
    if Saro:
        pass
    
    # Melchior et al. 2017 (default)
    logM0, Flam, Gz, lam0, z0 = 14.371, 1.12, 0.18, 30.0, 0.5
    Mhalo = 10**logM0 * (richness / lam0)**Flam * ( (1 + redshift) / (1 + z0) )**Gz
    
    return Mhalo
