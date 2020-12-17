"""
legacyhalos.io
==============

Code to read and write the various legacyhalos files.

"""
import os, pdb
import numpy as np
import numpy.ma as ma

import fitsio
import astropy.units as u
from astropy.table import Table, Column
from astrometry.util.fits import fits_table

def legacyhalos_dir():
    if 'LEGACYHALOS_DIR' not in os.environ:
        print('Required ${LEGACYHALOS_DIR environment variable not set.')
        raise EnvironmentError
    ldir = os.path.abspath(os.getenv('LEGACYHALOS_DIR'))
    if not os.path.isdir(ldir):
        os.makedirs(ldir, exist_ok=True)
    return ldir

def legacyhalos_data_dir():
    if 'LEGACYHALOS_DATA_DIR' not in os.environ:
        print('Required ${LEGACYHALOS_DATA_DIR environment variable not set.')
        raise EnvironmentError
    ldir = os.path.abspath(os.getenv('LEGACYHALOS_DATA_DIR'))
    if not os.path.isdir(ldir):
        os.makedirs(ldir, exist_ok=True)
    return ldir

def legacyhalos_html_dir():
    if 'LEGACYHALOS_HTML_DIR' not in os.environ:
        print('Required ${LEGACYHALOS_HTML_DIR environment variable not set.')
        raise EnvironmentError
    ldir = os.path.abspath(os.getenv('LEGACYHALOS_HTML_DIR'))
    if not os.path.isdir(ldir):
        os.makedirs(ldir, exist_ok=True)
    return ldir

# build out the FITS header
def legacyhalos_header(hdr=None):
    """Build a header with code versions, etc.

    """
    import subprocess
    from astropy.io import fits
    import pydl
    import legacyhalos

    if False:
        if hdr is None:
            hdr = fitsio.FITSHDR()

        cmd = 'cd {} && git describe --tags'.format(os.path.dirname(legacyhalos.__file__))
        ver = subprocess.check_output(cmd, shell=True, universal_newlines=True).strip()
        hdr.add_record(dict(name='LEGHALOV', value=ver, comment='legacyhalos git version'))

        depvers, headers = [], []
        for name, pkg in [('pydl', pydl)]:
            hdr.add_record(dict(name=name, value=pkg.__version__, comment='{} version'.format(name)))
    else:
        if hdr is None:
            hdr = fits.header.Header()

        cmd = 'cd {} && git describe --tags'.format(os.path.dirname(legacyhalos.__file__))
        ver = subprocess.check_output(cmd, shell=True, universal_newlines=True).strip()
        hdr['LEGHALOV'] = (ver, 'legacyhalos git version')

        depvers, headers = [], []
        for name, pkg in [('pydl', pydl)]:
            hdr[name] = (pkg.__version__, '{} version'.format(name))

    return hdr
    
def _missing_files_one(args):
    """Wrapper for the multiprocessing."""
    return missing_files_one(*args)

def missing_files_one(checkfile, dependsfile, clobber):
#def missing_files_one(galaxy, galaxydir, filesuffix, dependson, clobber):
    #checkfile = os.path.join(galaxydir, '{}{}'.format(galaxy, filesuffix))
    #print('missing_files_one: ', checkfile)
    #print(checkfile, dependsfile, clobber)
    if os.path.isfile(checkfile) and clobber is False:
        # Is the stage that this stage depends on done, too?
        #print(checkfile, dependsfile, clobber)
        if dependsfile is None:
            return 'done'
        else:
            if os.path.isfile(dependsfile):
                return 'done'
            else:
                return 'todo'
    else:
        #print('missing_files_one: ', checkfile)
        # Did this object fail?
        if checkfile[-6:] == 'isdone':
            failfile = checkfile[:-6]+'isfail'
            if os.path.isfile(failfile):
                if clobber is False:
                    return 'fail'
                else:
                    os.remove(failfile)
                    return 'todo'
            #if dependsfile is None:
            #    return 'todo'
            #else:
            #    if os.path.isfile(dependsfile):
            #        return 'todo'
            #    else:
            #        return 'todo'
        return 'todo'
    
def get_run(onegal, racolumn='RA', deccolumn='DEC'):
    """Get the run based on a simple declination cut."""
    if onegal[deccolumn] > 32.375:
        if onegal[racolumn] < 45 or onegal[racolumn] > 315:
            run = 'south'
        else:
            run = 'north'
    else:
        run = 'south'
    return run

# ellipsefit data model
def _get_ellipse_datamodel(sbthresh, bands=['g', 'r', 'z']):
    cols = [
        ('bands', ''),
        ('refband', ''),
        ('refpixscale', u.arcsec / u.pixel),
        ('success', ''),
        ('fitgeometry', ''),
        ('input_ellipse', ''),
        ('largeshift', ''),

        ('ra_x0', u.degree),
        ('dec_y0', u.degree),
        ('x0', u.pixel),
        ('y0', u.pixel),
        ('eps', ''),
        ('pa', u.degree),
        ('theta', u.degree),
        ('majoraxis', u.pixel),
        ('maxsma', u.pixel),

        ('integrmode', ''),
        ('sclip', ''),
        ('nclip', ''),

        #('psfsigma_g', u.pixel),
        #('psfsigma_r', u.pixel),
        #('psfsigma_z', u.pixel),

        ('psfsize_g', u.arcsec),
        #('psfsize_min_g', u.arcsec),
        #('psfsize_max_g', u.arcsec),
        ('psfsize_r', u.arcsec),
        #('psfsize_min_r', u.arcsec),
        #('psfsize_max_r', u.arcsec),
        ('psfsize_z', u.arcsec),
        #('psfsize_min_z', u.arcsec),
        #('psfsize_max_z', u.arcsec),

        ('psfdepth_g', u.mag),
        #('psfdepth_min_g', u.mag),
        #('psfdepth_max_g', u.mag),
        ('psfdepth_r', u.mag),
        #('psfdepth_min_r', u.mag),
        #('psfdepth_max_r', u.mag),
        ('psfdepth_z', u.mag),
        #('psfdepth_min_z', u.mag),
        #('psfdepth_max_z', u.mag),

        ('mw_transmission_g', ''),
        ('mw_transmission_r', ''),
        ('mw_transmission_z', ''),

        ('refband_width', u.pixel),
        ('refband_height', u.pixel)]

    for band in bands:
        cols.append(('{}_sma'.format(band), u.pixel))
        cols.append(('{}_intens'.format(band), u.maggy/u.arcsec**2))
        cols.append(('{}_intens_err'.format(band), u.maggy/u.arcsec**2))
        cols.append(('{}_eps'.format(band), ''))
        cols.append(('{}_eps_err'.format(band), ''))
        cols.append(('{}_pa'.format(band), u.degree))
        cols.append(('{}_pa_err'.format(band), u.degree))
        cols.append(('{}_x0'.format(band), u.pixel))
        cols.append(('{}_x0_err'.format(band), u.pixel))
        cols.append(('{}_y0'.format(band), u.pixel))
        cols.append(('{}_y0_err'.format(band), u.pixel))
        cols.append(('{}_a3'.format(band), '')) # units?
        cols.append(('{}_a3_err'.format(band), ''))
        cols.append(('{}_a4'.format(band), ''))
        cols.append(('{}_a4_err'.format(band), ''))
        cols.append(('{}_rms'.format(band), u.maggy/u.arcsec**2))
        cols.append(('{}_pix_stddev'.format(band), u.maggy/u.arcsec**2))
        cols.append(('{}_stop_code'.format(band), ''))
        cols.append(('{}_ndata'.format(band), ''))
        cols.append(('{}_nflag'.format(band), ''))
        cols.append(('{}_niter'.format(band), ''))
        cols.append(('{}_cog_sma'.format(band), u.arcsec))
        cols.append(('{}_cog_mag'.format(band), u.mag))
        cols.append(('{}_cog_magerr'.format(band), u.mag))
        cols.append(('{}_cog_params_mtot'.format(band), u.mag))
        cols.append(('{}_cog_params_m0'.format(band), u.mag))
        cols.append(('{}_cog_params_alpha1'.format(band), ''))
        cols.append(('{}_cog_params_alpha2'.format(band), ''))
        cols.append(('{}_cog_params_chi2'.format(band), ''))

    for thresh in sbthresh:
        cols.append(('radius_sb{:0g}'.format(thresh), u.arcsec))
        cols.append(('radius_sb{:0g}_err'.format(thresh), u.arcsec))
        
    for band in bands:
        for thresh in sbthresh:
            cols.append(('{}_mag_sb{:0g}'.format(band, thresh), u.mag))
            cols.append(('{}_mag_sb{:0g}_err'.format(band, thresh), u.mag))

    return cols

def write_ellipsefit(galaxy, galaxydir, ellipsefit, filesuffix='', galaxyid='',
                     galaxyinfo=None, refband='r', sbthresh=None, verbose=False):
    """Write out a FITS file based on the output of
    legacyhalos.ellipse.ellipse_multiband..

    ellipsefit - input dictionary

    """
    from astropy.io import fits
    from astropy.table import QTable

    if galaxyid.strip() == '':
        galid = ''
    else:
        galid = '-{}'.format(galaxyid)
    if filesuffix.strip() == '':
        fsuff = ''
    else:
        fsuff = '-{}'.format(filesuffix)
        
    ellipsefitfile = os.path.join(galaxydir, '{}{}{}-ellipse.fits'.format(galaxy, fsuff, galid))

    if sbthresh is None:
        from legacyhalos.ellipse import REF_SBTHRESH as sbthresh
    
    # Turn the ellipsefit dictionary into a FITS table, starting with the
    # galaxyinfo dictionary (if provided).
    out = QTable()
    if galaxyinfo:
        for key in galaxyinfo.keys():
            data = galaxyinfo[key][0]
            if np.isscalar(data):
                data = np.atleast_1d(data)
            else:
                data = np.atleast_2d(data)
            unit = galaxyinfo[key][1] # add units
            if type(unit) is not str:
                #data *= unit
                data = u.Quantity(value=data, unit=unit, dtype=data.dtype)
            col = Column(name=key, data=data)
            out.add_column(col)

    # First, unpack the nested dictionaries.
    datadict = {}
    for key in ellipsefit.keys():
        #if type(ellipsefit[key]) is dict: # obsolete
        #    for key2 in ellipsefit[key].keys():
        #        datadict['{}_{}'.format(key, key2)] = ellipsefit[key][key2]
        #else:
        #    datadict[key] = ellipsefit[key]
        datadict[key] = ellipsefit[key]
    del ellipsefit

    # Add to the data table
    datakeys = datadict.keys()
    for key, unit in _get_ellipse_datamodel(sbthresh):
        if key not in datakeys:
            raise ValueError('Data model change -- no column {} for galaxy {}!'.format(key, galaxy))
        data = datadict[key]
        if np.isscalar(data):# or len(np.array(data)) > 1:
            data = np.atleast_1d(data)
        #elif len(data) == 0:
        #    data = np.atleast_1d(data)
        else:
            data = np.atleast_2d(data)
        if type(unit) is not str:
            data = u.Quantity(value=data, unit=unit, dtype=data.dtype)
        col = Column(name=key, data=data)
        #if 'z_cog' in key:
        #    print(key)
        #    pdb.set_trace()
        out.add_column(col)

    if np.logical_not(np.all(np.isin([*datakeys], out.colnames))):
        raise ValueError('Data model change -- non-documented columns have been added to ellipsefit dictionary!')

    # uppercase!
    for col in out.colnames:
        out.rename_column(col, col.upper())

    hdr = legacyhalos_header()

    #for col in out.colnames:
    #    print(col, out[col])
    hdu = fits.convenience.table_to_hdu(out)
    hdu.header['EXTNAME'] = 'ELLIPSE'
    hdu.header.update(hdr)
    hdu.add_checksum()

    if verbose:
        print('Writing {}'.format(ellipsefitfile))
    hdu0 = fits.PrimaryHDU()
    hdu0.header['EXTNAME'] = 'PRIMARY'
    hx = fits.HDUList([hdu0, hdu])
    hx.writeto(ellipsefitfile, overwrite=True, checksum=True)
    #out.write(ellipsefitfile, overwrite=True)
    #fitsio.write(ellipsefitfile, out.as_array(), extname='ELLIPSE', header=hdr, clobber=True)

def read_ellipsefit(galaxy, galaxydir, filesuffix='', galaxyid='', verbose=True):
    """Read the output of write_ellipsefit. Convert the astropy Table into a
    dictionary so we can use a bunch of legacy code.

    """
    if galaxyid.strip() == '':
        galid = ''
    else:
        galid = '-{}'.format(galaxyid)
    if filesuffix.strip() == '':
        fsuff = ''
    else:
        fsuff = '-{}'.format(filesuffix)

    ellipsefitfile = os.path.join(galaxydir, '{}{}{}-ellipse.fits'.format(galaxy, fsuff, galid))
        
    if os.path.isfile(ellipsefitfile):
        data = Table.read(ellipsefitfile)

        # Convert (back!) into a dictionary.
        ellipsefit = {}
        for key in data.colnames:
            val = data[key].tolist()[0]
            if np.logical_not(np.isscalar(val)) and len(val) > 0:
                val = np.array(val)
            ellipsefit[key.lower()] = val # lowercase!
    else:
        if verbose:
            print('File {} not found!'.format(ellipsefitfile))
        ellipsefit = dict()

    return ellipsefit

def write_sersic(galaxy, galaxydir, sersic, modeltype='single', verbose=False):
    """Pickle a dictionary of photutils.isophote.isophote.IsophoteList objects (see,
    e.g., ellipse.fit_multiband).

    """
    sersicfile = os.path.join(galaxydir, '{}-sersic-{}.p'.format(galaxy, modeltype))
    if verbose:
        print('Writing {}'.format(sersicfile))
    with open(sersicfile, 'wb') as ell:
        pickle.dump(sersic, ell, protocol=2)

def read_sersic(galaxy, galaxydir, modeltype='single', verbose=True):
    """Read the output of write_sersic."""

    sersicfile = os.path.join(galaxydir, '{}-sersic-{}.p'.format(galaxy, modeltype))
    try:
        with open(sersicfile, 'rb') as ell:
            sersic = pickle.load(ell)
    except:
        #raise IOError
        if verbose:
            print('File {} not found!'.format(sersicfile))
        sersic = dict()

    return sersic

def write_sbprofile(sbprofile, smascale, sbfile):
    """Write a (previously derived) surface brightness profile as a simple ASCII
    file, for use on a webpage.

    """
    data = np.array( [
        sbprofile['sma'],
        sbprofile['sma'] * smascale,
        sbprofile['mu_g'],
        sbprofile['mu_r'],
        sbprofile['mu_z'],
        sbprofile['mu_g_err'],
        sbprofile['mu_r_err'],
        sbprofile['mu_z_err']
        ] ).T

    fixnan = np.isnan(data)
    if np.sum(fixnan) > 0:
        data[fixnan] = -999
        
    np.savetxt(sbfile, data, fmt='%.6f')
    #with open(sbfile, 'wb') as sb:
    #    sb.write('# Yo\n')
    #pdb.set_trace()

    print('Wrote {}'.format(sbfile))

def _get_psfsize_and_depth(tractor, bands, pixscale, incenter=False):
    """Support function for read_multiband. Compute the average PSF size (in arcsec)
    and depth (in 5-sigma AB mags) in each bandpass based on the Tractor
    catalog.

    """
    out = {}

    # Optionally choose sources in the center of the field.
    H = np.max(tractor.bx) - np.min(tractor.bx)
    W = np.max(tractor.by) - np.min(tractor.by)
    if incenter:
        dH = 0.1 * H
        these = np.where((tractor.bx >= np.int(H / 2 - dH)) * (tractor.bx <= np.int(H / 2 + dH)) *
                         (tractor.by >= np.int(H / 2 - dH)) * (tractor.by <= np.int(H / 2 + dH)))[0]
    else:
        #these = np.where(tractor.get(psfdepthcol) > 0)[0]
        these = np.arange(len(tractor))
    
    # Get the average PSF size and depth in each bandpass.
    for filt in bands:
        psfsizecol = 'psfsize_{}'.format(filt.lower())
        psfdepthcol = 'psfdepth_{}'.format(filt.lower())
        if psfsizecol in tractor.columns():
            good = np.where(tractor.get(psfsizecol)[these] > 0)[0]
            if len(good) == 0:
                print('  No good measurements of the PSF size in band {}!'.format(filt))
                out['psfsigma_{}'.format(filt)] = np.float32(0.0)
                out['psfsize_{}'.format(filt)] = np.float32(0.0)
            else:
                # Get the PSF size and image depth.
                psfsize = tractor.get(psfsizecol)[these][good]   # [FWHM, arcsec]
                psfsigma = psfsize / np.sqrt(8 * np.log(2)) / pixscale # [sigma, pixels]

                out['psfsigma_{}'.format(filt)] = np.median(psfsigma).astype('f4') 
                out['psfsize_{}'.format(filt)] = np.median(psfsize).astype('f4') 
            
        if psfsizecol in tractor.columns():
            good = np.where(tractor.get(psfdepthcol)[these] > 0)[0]
            if len(good) == 0:
                print('  No good measurements of the PSF depth in band {}!'.format(filt))
                out['psfdepth_{}'.format(filt)] = np.float32(0.0)
            else:
                psfdepth = tractor.get(psfdepthcol)[these][good] # [AB mag, 5-sigma]
                out['psfdepth_{}'.format(filt)] = (22.5-2.5*np.log10(1/np.sqrt(np.median(psfdepth)))).astype('f4') 
        
    return out

def _read_data(data, filt2imfile, starmask=None, fill_value=0.0,
               verbose=False):
    """Helper function for read_multiband. Read the multi-band images and inverse
    variance images and pack them into a dictionary. Also create an initial
    pixel-level mask and handle images with different pixel scales (e.g., GALEX
    and WISE images).

    """
    from astropy.stats import sigma_clipped_stats
    from scipy.ndimage.morphology import binary_dilation
    from scipy.ndimage.filters import gaussian_filter
    from skimage.transform import resize

    from tractor.psf import PixelizedPSF
    from tractor.tractortime import TAITime
    from astrometry.util.util import Tan
    from legacypipe.survey import LegacySurveyWcs

    bands, refband = data['bands'], data['refband']

    # Loop on each filter and return the masked data.
    residual_mask = None
    for filt in bands:
        # Read the data and initialize the mask with the inverse variance image,
        # if available.
        if verbose:
            print('Reading {}'.format(filt2imfile[filt]['image']))
            print('Reading {}'.format(filt2imfile[filt]['model']))
        image = fitsio.read(filt2imfile[filt]['image'])
        model = fitsio.read(filt2imfile[filt]['model'])
        sz = image.shape

        # optional additional (scalar) sky-subtraction
        if 'sky' in filt2imfile[filt].keys():
            #print('Subtracting!!! ', filt2imfile[filt]['sky'])
            image += filt2imfile[filt]['sky']
            model += filt2imfile[filt]['sky']

        # GALEX, unWISE need to be resized.
        if starmask.shape == sz:
            doresize = False
        else:
            doresize = True

        # Initialize the mask based on the inverse variance
        if 'invvar' in filt2imfile[filt].keys():
            if verbose:
                print('Reading {}'.format(filt2imfile[filt]['invvar']))
            invvar = fitsio.read(filt2imfile[filt]['invvar'])
            mask = invvar <= 0 # True-->bad, False-->good
        else:
            invvar = None
            mask = np.zeros_like(image).astype(bool)

        # Build the PSF and WCS in the reference band.
        if filt == refband:
            HH, WW = sz
            data['refband_width'] = WW
            data['refband_height'] = HH
            refhdr = fitsio.read_header(filt2imfile[filt]['image'], ext=1)

            if verbose:
                print('Reading {}'.format(filt2imfile[refband]['psf']))
            psfimg = fitsio.read(filt2imfile[refband]['psf'])
            data['refband_psf'] = PixelizedPSF(psfimg)

            wcs = Tan(filt2imfile[refband]['image'], 1)
            mjd_tai = refhdr['MJD_MEAN'] # [TAI]

            data['wcs'] = LegacySurveyWcs(wcs, TAITime(None, mjd=mjd_tai))

        # Add in the star mask, resizing if necessary for this image/pixel scale.
        if doresize:
            _starmask = resize(starmask, mask.shape, mode='reflect')
            mask = np.logical_or(mask, _starmask)
        else:
            mask = np.logical_or(mask, starmask)

        # Flag significant residual pixels after subtracting *all* the models
        # (we will restore the pixels of the galaxies of interest below).
        resid = gaussian_filter(image - model, 2.0)
        _, _, sig = sigma_clipped_stats(resid, sigma=3.0)
        if residual_mask is None:
            residual_mask = np.abs(resid) > 5*sig
        else:
            _residual_mask = np.abs(resid) > 5*sig
            if doresize:
                _residual_mask = resize(_residual_mask, residual_mask.shape, mode='reflect')
            residual_mask = np.logical_or(residual_mask, _residual_mask)

        # Dilate the mask, mask out a 10% border, and pack into a dictionary.
        mask = binary_dilation(mask, iterations=2)
        edge = np.int(0.02*sz[0])
        mask[:edge, :] = True
        mask[:, :edge] = True
        mask[:, sz[0]-edge:] = True
        mask[sz[0]-edge:, :] = True

        data[filt] = ma.masked_array(image, mask) # [nanomaggies]
        ma.set_fill_value(data[filt], fill_value)

        if invvar is not None:
            var = np.zeros_like(invvar)
            ok = invvar > 0
            var[ok] = 1 / invvar[ok]
            data['{}_var_'.format(filt)] = var # [nanomaggies**2]
            #data['{}_var'.format(filt)] = var / thispixscale**4 # [nanomaggies**2/arcsec**4]
            if np.any(invvar < 0):
                print('Warning! Negative pixels in the {}-band inverse variance map!'.format(filt))
                #pdb.set_trace()

    data['residual_mask'] = residual_mask

    return data

def _largegalaxy_sample():
    """Read 


    """

def _largegalaxy_mask(data, tractor, filt2pixscale, fill_value=0.0,
                      central_galaxy=None, central_galaxy_id=None,
                      verbose=False):
    """Wrapper to prepare the data for the SGA / large-galaxy project.

    """
    from legacyhalos.mge import find_galaxy
    from legacyhalos.misc import srcs2image, ellipse_mask

    bands, refband = data['bands'], data['refband']
    residual_mask = data['residual_mask']

    nbox = 5
    box = np.arange(nbox)-nbox // 2
    #box = np.meshgrid(np.arange(nbox), np.arange(nbox))[0]-nbox//2

    xobj, yobj = np.ogrid[0:data['refband_height'], 0:data['refband_width']]

    # If the row-index of the central galaxy is not provided, use the source
    # nearest to the center of the field.
    if central_galaxy is None:
        central_galaxy = np.array([np.argmin((tractor.bx - data['refband_height']/2)**2 + (tractor.by - data['refband_width']/2)**2)])
        central_galaxy_id = None
    data['central_galaxy_id'] = central_galaxy_id

    #print('Import hack!')
    #import matplotlib.pyplot as plt ; from astropy.visualization import simple_norm
    
    # Now, loop through each 'central_galaxy' from bright to faint.
    data['mge'] = []
    for ii, central in enumerate(central_galaxy):
        if verbose:
            print('Building masked image for central {}/{}.'.format(ii+1, len(central_galaxy)))

        # Build the model image (of every object except the central)
        # on-the-fly. Need to be smarter about Tractor sources of resolved
        # structure (i.e., sources that "belong" to the central).
        nocentral = np.delete(np.arange(len(tractor)), central)
        srcs = tractor.copy()
        srcs.cut(nocentral)
        model_nocentral = srcs2image(srcs, data['wcs'], band=refband.lower(),
                                     pixelized_psf=data['refband_psf'])

        # Mask all previous (brighter) central galaxies, if any.
        img, newmask = ma.getdata(data[refband]) - model_nocentral, ma.getmask(data[refband])
        for jj in np.arange(ii):
            geo = data['mge'][jj] # the previous galaxy

            # Do this step iteratively to capture the possibility where the
            # previous galaxy has masked the central pixels of the *current*
            # galaxy, in each iteration reducing the size of the mask.
            for shrink in np.arange(0.1, 1.05, 0.05)[::-1]:
                maxis = shrink * geo['majoraxis']
                _mask = ellipse_mask(geo['xmed'], geo['ymed'], maxis, maxis * (1-geo['eps']),
                                     np.radians(geo['theta']-90), xobj, yobj)
                notok = False
                for xb in box:
                    for yb in box:
                        if _mask[int(yb+tractor.by[central]), int(xb+tractor.bx[central])]:
                            notok = True
                            break
                if notok:
                #if _mask[int(tractor.by[central]), int(tractor.bx[central])]:
                    print('The previous central has masked the current central with shrink factor {:.2f}'.format(shrink))
                else:
                    break
            newmask = ma.mask_or(_mask, newmask)

        # Next, get the basic galaxy geometry and pack it into a dictionary. If
        # the object of interest has been masked by, e.g., an adjacent star
        # (see, e.g., IC4041), temporarily unmask those pixels using the Tractor
        # geometry.
        
        minsb = 10**(-0.4*(27.5-22.5)) / filt2pixscale[refband]**2
        #import matplotlib.pyplot as plt ; plt.clf()
        #mgegalaxy = find_galaxy(img / filt2pixscale[refband]**2, nblob=1, binning=3, quiet=not verbose, plot=True, level=minsb)
        #mgegalaxy = find_galaxy(img / filt2pixscale[refband]**2, nblob=1, fraction=0.1, binning=3, quiet=not verbose, plot=True)
        notok, val = False, []
        for xb in box:
            for yb in box:
                #print(xb, yb, val)
                val.append(newmask[int(yb+tractor.by[central]), int(xb+tractor.bx[central])])
                
        # Use np.any() here to capture the case where a handful of the central
        # pixels are masked due to, e.g., saturation, which if we don't do, will
        # cause issues in the ellipse-fitting (specifically with
        # CentralEllipseFitter(censamp).fit() if the very central pixel is
        # masked).  For a source masked by a star, np.all() would have worked
        # fine.
        if np.any(val):
            notok = True
            
        if notok:
            print('Central position has been masked, possibly by a star (or saturated core).')
            xmed, ymed = tractor.by[central], tractor.bx[central]
            #if largegalaxy:
            #    ba = tractor.ba_leda[central]
            #    pa = tractor.pa_leda[central]
            #    maxis = tractor.d25_leda[central] * 60 / 2 / filt2pixscale[refband] # [pixels]
            ee = np.hypot(tractor.shape_e1[central], tractor.shape_e2[central])
            ba = (1 - ee) / (1 + ee)
            pa = 180 - (-np.rad2deg(np.arctan2(tractor.shape_e2[central], tractor.shape_e1[central]) / 2))
            pa = pa % 180
            maxis = 1.5 * tractor.shape_r[central] / filt2pixscale[refband] # [pixels]
            theta = (270 - pa) % 180
                
            fixmask = ellipse_mask(xmed, ymed, maxis, maxis*ba, np.radians(theta-90), xobj, yobj)
            newmask[fixmask] = ma.nomask
        
        #import matplotlib.pyplot as plt ; plt.clf()
        mgegalaxy = find_galaxy(ma.masked_array(img/filt2pixscale[refband]**2, newmask), 
                                nblob=1, binning=3, level=minsb)#, plot=True)#, quiet=not verbose
        #plt.savefig('junk.png') ; pdb.set_trace()

        # Above, we used the Tractor positions, so check one more time here with
        # the light-weighted positions, which may have shifted into a masked
        # region (e.g., check out the interacting pair PGC052639 & PGC3098317).
        val = []
        for xb in box:
            for yb in box:
                val.append(newmask[int(xb+mgegalaxy.xmed), int(yb+mgegalaxy.ymed)])
        if np.any(val):
            notok = True

        # If we fit the geometry by unmasking pixels using the Tractor fit then
        # we're probably sitting inside the mask of a bright star, so call
        # find_galaxy a couple more times to try to grow the "unmasking".
        if notok:
            print('Iteratively unmasking pixels:')
            maxis = 1.0 * mgegalaxy.majoraxis # [pixels]
            print('  r={:.2f} pixels'.format(maxis))
            prevmaxis, iiter, maxiter = 0.0, 0, 4
            while (maxis > prevmaxis) and (iiter < maxiter):
                #print(prevmaxis, maxis, iiter, maxiter)
                print('  r={:.2f} pixels'.format(maxis))
                fixmask = ellipse_mask(mgegalaxy.xmed, mgegalaxy.ymed,
                                       maxis, maxis * (1-mgegalaxy.eps), 
                                       np.radians(mgegalaxy.theta-90), xobj, yobj)
                newmask[fixmask] = ma.nomask
                mgegalaxy = find_galaxy(ma.masked_array(img/filt2pixscale[refband]**2, newmask), 
                                        nblob=1, binning=3, quiet=True, plot=False, level=minsb)
                prevmaxis = maxis.copy()
                maxis = 1.2 * mgegalaxy.majoraxis # [pixels]
                iiter += 1

        #plt.savefig('junk.png') ; pdb.set_trace()
        print(mgegalaxy.xmed, tractor.by[central], mgegalaxy.ymed, tractor.bx[central])
        maxshift = 10
        if (np.abs(mgegalaxy.xmed-tractor.by[central]) > maxshift or # note [xpeak,ypeak]-->[by,bx]
            np.abs(mgegalaxy.ymed-tractor.bx[central]) > maxshift):
            print('Peak position has moved by more than {} pixels---falling back on Tractor geometry!'.format(maxshift))
            #import matplotlib.pyplot as plt ; plt.clf()
            #mgegalaxy = find_galaxy(ma.masked_array(img/filt2pixscale[refband]**2, newmask), nblob=1, binning=3, quiet=False, plot=True, level=minsb)
            #plt.savefig('junk.png') ; pdb.set_trace()
            #pdb.set_trace()
            largeshift = True
            
            ee = np.hypot(tractor.shape_e1[central], tractor.shape_e2[central])
            ba = (1 - ee) / (1 + ee)
            pa = 180 - (-np.rad2deg(np.arctan2(tractor.shape_e2[central], tractor.shape_e1[central]) / 2))
            mgegalaxy.xmed = tractor.by[central]
            mgegalaxy.ymed = tractor.bx[central]
            mgegalaxy.xpeak = tractor.by[central]
            mgegalaxy.ypeak = tractor.bx[central]
            mgegalaxy.eps = 1 - ba
            mgegalaxy.pa = pa % 180
            mgegalaxy.theta = (270 - pa) % 180
            mgegalaxy.majoraxis = 2 * tractor.shape_r[central] / filt2pixscale[refband] # [pixels]
            print('  r={:.2f} pixels'.format(mgegalaxy.majoraxis))
            fixmask = ellipse_mask(mgegalaxy.xmed, mgegalaxy.ymed,
                                   mgegalaxy.majoraxis, mgegalaxy.majoraxis * (1-mgegalaxy.eps), 
                                   np.radians(mgegalaxy.theta-90), xobj, yobj)
            newmask[fixmask] = ma.nomask
        else:
            largeshift = False

        #if tractor.ref_id[central] == 474614:
        #    import matplotlib.pyplot as plt
        #    plt.imshow(mask, origin='lower')
        #    plt.savefig('junk.png')
        #    pdb.set_trace()
            
        radec_med = data['wcs'].pixelToPosition(mgegalaxy.ymed+1, mgegalaxy.xmed+1).vals
        radec_peak = data['wcs'].pixelToPosition(mgegalaxy.ypeak+1, mgegalaxy.xpeak+1).vals
        mge = {'largeshift': largeshift,
            'ra': tractor.ra[central], 'dec': tractor.dec[central],
            'bx': tractor.bx[central], 'by': tractor.by[central],
            'mw_transmission_g': tractor.mw_transmission_g[central],
            'mw_transmission_r': tractor.mw_transmission_r[central],
            'mw_transmission_z': tractor.mw_transmission_z[central],
            'ra_x0': radec_med[0], 'dec_y0': radec_med[1],
            #'ra_peak': radec_med[0], 'dec_peak': radec_med[1]
            }
        for key in ('eps', 'majoraxis', 'pa', 'theta', 'xmed', 'ymed', 'xpeak', 'ypeak'):
            mge[key] = np.float32(getattr(mgegalaxy, key))
            if key == 'pa': # put into range [0-180]
                mge[key] = mge[key] % np.float32(180)
        data['mge'].append(mge)

        # Now, loop on each filter and build a custom image and mask for each
        # central. Specifically, pack the model-subtracted images images
        # corresponding to each (unique) central into a list. Note that there's
        # a little bit of code to deal with different pixel scales but this case
        # requires more work.
        
        #for filt in [refband]:
        for filt in bands:
            thispixscale = filt2pixscale[filt]
            
            imagekey, varkey = '{}_masked'.format(filt), '{}_var'.format(filt)
            if imagekey not in data.keys():
                data[imagekey], data[varkey] = [], []

            factor = filt2pixscale[refband] / filt2pixscale[filt]
            majoraxis = 1.5 * factor * mgegalaxy.majoraxis # [pixels]

            # Grab the pixels belonging to this galaxy so we can unmask them below.
            central_mask = ellipse_mask(mge['xmed'] * factor, mge['ymed'] * factor, 
                                        majoraxis, majoraxis * (1-mgegalaxy.eps), 
                                        np.radians(mgegalaxy.theta-90), xobj, yobj)
            if np.sum(central_mask) == 0:
                print('No pixels belong to the central galaxy---this is bad!')
                data['failed'] = True
                break

            # Build the mask from the (cumulative) residual-image mask and the
            # inverse variance mask for this galaxy, but then "unmask" the
            # pixels belonging to the central.
            _residual_mask = residual_mask.copy()
            _residual_mask[central_mask] = ma.nomask
            mask = ma.mask_or(_residual_mask, newmask, shrink=False)

            #import matplotlib.pyplot as plt
            #plt.clf() ; plt.imshow(central_mask, origin='lower') ; plt.savefig('junk2.png')
            #pdb.set_trace()

            # Need to be smarter about the srcs list...
            srcs = tractor.copy()
            srcs.cut(nocentral)
            model_nocentral = srcs2image(srcs, data['wcs'], band=filt.lower(),
                                         pixelized_psf=data['refband_psf'])

            # Convert to surface brightness and 32-bit precision.
            img = (ma.getdata(data[filt]) - model_nocentral) / thispixscale**2 # [nanomaggies/arcsec**2]
            img = ma.masked_array(img.astype('f4'), mask)
            var = data['{}_var_'.format(filt)] / thispixscale**4 # [nanomaggies**2/arcsec**4]

            # Fill with zeros, for fun--
            ma.set_fill_value(img, fill_value)
            #img.filled(fill_value)
            data[imagekey].append(img)
            data[varkey].append(var)

            #if tractor.ref_id[central] == 474614:
            #    import matplotlib.pyplot as plt ; from astropy.visualization import simple_norm ; plt.clf()
            #    thisimg = np.log10(data[imagekey][ii]) ; norm = simple_norm(thisimg, 'log') ; plt.imshow(thisimg, origin='lower', norm=norm) ; plt.savefig('junk{}.png'.format(ii+1))
            #    pdb.set_trace()


    # Cleanup?
    for filt in bands:
        del data[filt]
        del data['{}_var_'.format(filt)]

    return data            

def _read_and_mask(data, filt2imfile, filt2pixscale, tractor,
                   fill_value=0.0,
                   central_galaxy=None, central_galaxy_id=None,
                   starmask=None, verbose=False,
                   cluster=True, largegalaxy=False):
    """Helper function for read_multiband. Read the multi-band imaging and build a
    mask.

    central_galaxy - indices of objects in the tractor catalog to *not* mask

    """
    # Read the initial data.
    data = _read_data(data, filt2imfile, starmask=starmask,
                      fill_value=fill_value, verbose=verbose)

    largegalaxy = True
    if largegalaxy:
        data = _largegalaxy_mask(data, tractor, filt2pixscale,
                                 fill_value=fill_value,
                                 central_galaxy=central_galaxy,
                                 central_galaxy_id=central_galaxy_id,
                                 verbose=verbose)
    elif cluster:
        pass
    else:
        raise NotImplemented('Write me!')

    pdb.set_trace()
            
    return data

def read_multiband(galaxy, galaxydir, bands=('g', 'r', 'z'), refband='r',
                   pixscale=0.262, galex_pixscale=1.5, unwise_pixscale=2.75,
                   sdss_pixscale=0.396, return_sample=False,
                   galex=False, unwise=False,
                   subsky={},
                   #central_galaxy_id=None,
                   sdss=False, largegalaxy=False, pipeline=False, verbose=False):
    """Read the multi-band images (converted to surface brightness) and create a
    masked array suitable for ellipse-fitting.

    subsky - dictionary of additional scalar value to subtract from the imaging,
      per band, e.g., {'g': -0.01, 'r': 0.002, 'z': -0.0001}

    """
    from legacypipe.bits import MASKBITS

    # Dictionary mapping between optical filter and filename coded up in
    # coadds.py, galex.py, and unwise.py, which depends on the project.
    filt2imfile, filt2pixscale = {}, {}
    if sdss:
        masksuffix = 'sdss-mask-gri'
        bands = ('g', 'r', 'i')
        tractorprefix = None
        maskbitsprefix = None
        [filt2imfile.update({band: {'image': 'sdss-image',
                                    'model': 'sdss-model',
                                    'model-nocentral': 'sdss-model-nocentral'}}) for band in bands]
        [filt2pixscale.update({band: sdss_pixscale}) for band in bands]
    else:
        if largegalaxy:
            prefix = 'largegalaxy'
        elif pipeline:
            prefix = 'pipeline'
        else:
            prefix = 'custom'
            
        [filt2imfile.update({band: {'image': '{}-image'.format(prefix),
                                    'model': '{}-model'.format(prefix),
                                    'invvar': '{}-invvar'.format(prefix),
                                    'psf': '{}-psf'.format(prefix),
                                    'sky': 0.0}}) for band in bands]
        [filt2pixscale.update({band: pixscale}) for band in bands]

        # Add the tractor and maskbits files.
        filt2imfile.update({'tractor': '{}-tractor'.format(prefix),
                            'sample': '{}-sample'.format(prefix),
                            'maskbits': '{}-maskbits'.format(prefix)})

        # add optional sky-subtraction values
        if bool(subsky):
            for band in bands:
                if band in subsky.keys():
                    filt2imfile[band]['sky'] = subsky[band]

    # Add GALEX and unWISE--
    if galex:
        for band in ['FUV', 'NUV']:
            #bands = bands + tuple([band])
            filt2pixscale.update({band: galex_pixscale})
            filt2imfile.update({band: {'image': 'image', 'model': '{}-model'.format(prefix), 'invvar': 'invvar'}})
    if unwise:
        for band in ['W1', 'W2', 'W3', 'W4']:
            #bands = bands + tuple([band])
            filt2pixscale.update({band: unwise_pixscale})
            filt2imfile.update({band: {'image': 'image', 'model': '{}-model'.format(prefix), 'invvar': 'invvar'}})

    # Do all the files exist? If not, bail!
    found_data = True
    for filt in bands:
        for ii, imtype in enumerate(filt2imfile[filt].keys()):
            if imtype == 'sky': # skip this
                continue
            for suffix in ('.fz', ''):
                imfile = os.path.join(galaxydir, '{}-{}-{}.fits{}'.format(galaxy, filt2imfile[filt][imtype], filt, suffix))
                #print(imfile)
                if os.path.isfile(imfile):
                    filt2imfile[filt][imtype] = imfile
                    break
            if not os.path.isfile(imfile):
                if verbose:
                    print('File {} not found.'.format(imfile))
                found_data = False

    data = dict()
    if not found_data:
        if return_sample:
            return data, Table()
        else:
            return data

    # Pack some preliminary info into the dictionary.
    data['failed'] = False # be optimistic!
    data['bands'] = bands
    data['refband'] = refband
    data['refpixscale'] = np.float32(pixscale)

    if 'NUV' in bands:
        data['galex_pixscale'] = galex_pixscale
    if 'W1' in bands:
        data['unwise_pixscale'] = unwise_pixscale

    # Read the tractor and full-sample catalogs.
    samplefile = os.path.join(galaxydir, '{}-{}.fits'.format(galaxy, filt2imfile['sample']))
    if os.path.isfile(samplefile):
        sample = Table(fitsio.read(samplefile, upper=True))
        if verbose:
            print('Read {} galaxy(ies) from {}'.format(len(sample), samplefile))

    # We ~have~ to read using fits_table because we will turn these catalog
    # entries into Tractor sources later.
    tractorfile = os.path.join(galaxydir, '{}-{}.fits'.format(galaxy, filt2imfile['tractor']))
    if verbose:
        print('Reading {}'.format(tractorfile))
        
    #cols = ['BX', 'BY', 'TYPE', 'REF_CAT', 'REF_ID', 'SERSIC', 'SHAPE_R', 'FLUX_G', 'FLUX_R', 'FLUX_Z',
    #        'PSFDEPTH_G', 'PSFDEPTH_R', 'PSFDEPTH_Z', 'PSFSIZE_G', 'PSFSIZE_R', 'PSFSIZE_Z']
    #tractor = Table(fitsio.read(tractorfile, columns=cols, upper=True))
    cols = ['ra', 'dec', 'bx', 'by', 'type', 'ref_cat', 'ref_id',
            'sersic', 'shape_r', 'shape_e1', 'shape_e2',
            'flux_g', 'flux_r', 'flux_z',
            'flux_ivar_g', 'flux_ivar_r', 'flux_ivar_z',
            'nobs_g', 'nobs_r', 'nobs_z',
            'mw_transmission_g', 'mw_transmission_r', 'mw_transmission_z', 
            'psfdepth_g', 'psfdepth_r', 'psfdepth_z',
            'psfsize_g', 'psfsize_r', 'psfsize_z']
    if galex:
        cols = cols+['flux_fuv', 'flux_nuv']
    if unwise:
        cols = cols+['flux_w1', 'flux_w1', 'flux_w1', 'flux_w1']
    tractor = fits_table(tractorfile, columns=cols)
    hdr = fitsio.read_header(tractorfile)
    if verbose:
        print('Read {} sources from {}'.format(len(tractor), tractorfile))
    data.update(_get_psfsize_and_depth(tractor, bands, pixscale, incenter=False))

    # Read the maskbits image and build the starmask.
    maskbitsfile = os.path.join(galaxydir, '{}-{}.fits.fz'.format(galaxy, filt2imfile['maskbits']))
    if verbose:
        print('Reading {}'.format(maskbitsfile))
    maskbits = fitsio.read(maskbitsfile)
    # initialize the mask using the maskbits image
    starmask = ( (maskbits & MASKBITS['BRIGHT'] != 0) | (maskbits & MASKBITS['MEDIUM'] != 0) |
                 (maskbits & MASKBITS['CLUSTER'] != 0) | (maskbits & MASKBITS['ALLMASK_G'] != 0) |
                 (maskbits & MASKBITS['ALLMASK_R'] != 0) | (maskbits & MASKBITS['ALLMASK_Z'] != 0) )

    # Read the data. For the large-galaxy project, iterate on LSLGA galaxies in
    # the field, otherwise, take the object closest to the center of the mosaic
    # (which we figure out in _read_and_mask, after we know the size of the
    # mosaic).
    if largegalaxy:
        # I'm going to be pedantic here to be sure I get it right (np.isin
        # doens't preserve order)--
        msg = []
        islslga = ['L' in refcat for refcat in tractor.ref_cat] # e.g., L6
        minsize = 2.0     # [arcsec]
        minsize_rex = 5.0 # minimum size for REX [arcsec]
        central_galaxy, reject_galaxy, keep_galaxy = [], [], []
        data['tractor_flags'] = {}
        for ii, sid in enumerate(sample['SGA_ID']):
            I = np.where((sid == tractor.ref_id) * islslga)[0]
            if len(I) == 0: # dropped by Tractor
                reject_galaxy.append(ii)
                data['tractor_flags'].update({str(sid): 'dropped'})
                msg.append('Dropped by Tractor (spurious?)')
            else:
                r50 = tractor.shape_r[I][0]
                refflux = tractor.get('flux_{}'.format(refband))[I][0]
                # Bug in fit_on_coadds: nobs_[g,r,z] is 1 even when missing the
                # band, so use flux_ivar_[g,r,z].
                #ng, nr, nz = tractor.nobs_g[I][0], tractor.nobs_z[I][0], tractor.nobs_z[I][0]
                #if ng < 1 or nr < 1 or nz < 1:
                ng = tractor.flux_g[I][0] * np.sqrt(tractor.flux_ivar_g[I][0]) == 0
                nr = tractor.flux_r[I][0] * np.sqrt(tractor.flux_ivar_r[I][0]) == 0
                nz = tractor.flux_z[I][0] * np.sqrt(tractor.flux_ivar_z[I][0]) == 0
                if ng or nr or nz:
                    reject_galaxy.append(ii)
                    data['tractor_flags'].update({str(sid): 'nogrz'})
                    msg.append('Missing 3-band coverage')
                elif tractor.type[I] == 'PSF': # always reject
                    reject_galaxy.append(ii)
                    data['tractor_flags'].update({str(sid): 'psf'})
                    msg.append('Tractor type=PSF')
                elif refflux < 0:
                    reject_galaxy.append(ii)
                    data['tractor_flags'].update({str(sid): 'negflux'})
                    msg.append('{}-band flux={:.3g} (<=0)'.format(refband, refflux))
                elif r50 < minsize:
                    reject_galaxy.append(ii)
                    data['tractor_flags'].update({str(sid): 'anytype_toosmall'})
                    msg.append('type={}, r50={:.3f} (<{:.1f}) arcsec'.format(tractor.type[I], r50, minsize))
                elif tractor.type[I] == 'REX':
                    if r50 < minsize_rex: # REX must have a minimum size
                        reject_galaxy.append(ii)
                        data['tractor_flags'].update({str(sid): 'rex_toosmall'})
                        msg.append('Tractor type=REX & r50={:.3f} (<{:.1f}) arcsec'.format(r50, minsize_rex))
                    else:
                        keep_galaxy.append(ii)
                        central_galaxy.append(I)
                else:
                    keep_galaxy.append(ii)
                    central_galaxy.append(I)

        if len(reject_galaxy) > 0:
            reject_galaxy = np.hstack(reject_galaxy)
            for jj, rej in enumerate(reject_galaxy):
                print('  Dropping {} (SGA_ID={}, RA, Dec = {:.7f} {:.7f}): {}'.format(
                    sample[rej]['GALAXY'], sample[rej]['SGA_ID'], sample[rej]['RA'], sample[rej]['DEC'], msg[jj]))

        if len(central_galaxy) > 0:
            keep_galaxy = np.hstack(keep_galaxy)
            central_galaxy = np.hstack(central_galaxy)
            sample = sample[keep_galaxy]
        else:
            data['failed'] = True
            if return_sample:
                return data, Table()
            else:
                return data

        #sample = sample[np.searchsorted(sample['SGA_ID'], tractor.ref_id[central_galaxy])]
        assert(np.all(sample['SGA_ID'] == tractor.ref_id[central_galaxy]))
        
        tractor.d25_leda = np.zeros(len(tractor), dtype='f4')
        tractor.pa_leda = np.zeros(len(tractor), dtype='f4')
        tractor.ba_leda = np.zeros(len(tractor), dtype='f4')
        if 'D25_LEDA' in sample.colnames and 'PA_LEDA' in sample.colnames and 'BA_LEDA' in sample.colnames:
            tractor.d25_leda[central_galaxy] = sample['D25_LEDA']
            tractor.pa_leda[central_galaxy] = sample['PA_LEDA']
            tractor.ba_leda[central_galaxy] = sample['BA_LEDA']
        
        # Do we need to take into account the elliptical mask of each source??
        srt = np.argsort(tractor.flux_r[central_galaxy])[::-1]
        central_galaxy = central_galaxy[srt]
        print('Sort by flux! ', tractor.flux_r[central_galaxy])
        central_galaxy_id = tractor.ref_id[central_galaxy]
    else:
        sample = None
        central_galaxy, central_galaxy_id = None, None

    data = _read_and_mask(data, filt2imfile, filt2pixscale,
                          tractor, central_galaxy=central_galaxy,
                          central_galaxy_id=central_galaxy_id,
                          starmask=starmask, verbose=verbose,
                          largegalaxy=largegalaxy)
    
    #import matplotlib.pyplot as plt
    #plt.clf() ; plt.imshow(np.log10(data['g_masked'][0]), origin='lower') ; plt.savefig('junk1.png')
    ##plt.clf() ; plt.imshow(np.log10(data['r_masked'][1]), origin='lower') ; plt.savefig('junk2.png')
    ##plt.clf() ; plt.imshow(np.log10(data['r_masked'][2]), origin='lower') ; plt.savefig('junk3.png')
    #pdb.set_trace()

    if return_sample:
        return data, sample
    else:
        return data

