"""
legacyhalos.sdss
================

Code to handle the SDSS coadds.

"""
import os, time, copy, pdb
import subprocess
import numpy as np

import fitsio
from astrometry.util.multiproc import multiproc
from astrometry.util.fits import fits_table

import legacyhalos.io
import legacyhalos.misc
from legacyhalos.misc import custom_brickname
from legacyhalos.coadds import isolate_central

from legacyhalos.misc import RADIUS_CLUSTER_KPC

def _forced_phot(args):
    """Wrapper function for the multiprocessing."""
    return forced_phot(*args)

def forced_phot(galaxy, survey, srcs, band):
    """Perform forced photometry on a single SDSS bandpass (mosaic).

    """
    from astrometry.util.util import Tan
    from tractor.image import Image
    from tractor.sky import ConstantSky
    from tractor.basics import LinearPhotoCal
    from tractor import Tractor, ConstantFitsWcs, GaussianMixturePSF

    bandfile = os.path.join(survey.output_dir, '{}-sdss-image-{}.fits.fz'.format(galaxy, band))
    img, hdr = fitsio.read(bandfile, header=True)
    brickwcs = ConstantFitsWcs(Tan(hdr['CRVAL1'], hdr['CRVAL2'], hdr['CRPIX1'], hdr['CRPIX2'],
                                   hdr['CD1_1'], hdr['CD1_2'], hdr['CD2_1'], hdr['CD2_2'],
                                   hdr['NAXIS1'], hdr['NAXIS2']))

    # Estimate the PSF by fitting a simple Gaussian PSF to all the point sources.
        


    # ToDo: estimate the PSF from the image itself!
    psf_sigma = 1.3
    psf = GaussianMixturePSF(1.0, 0., 0., psf_sigma**2, psf_sigma**2, 0.0)
    tim = Image(img, wcs=brickwcs, psf=psf,
                invvar=np.ones_like(img), 
                sky=ConstantSky(0.0),
                photocal=LinearPhotoCal(1.0, band=band),
                name='SDSS {}'.format(band))

    # Instantiate the Tractor engine and do forced photometry.
    tractor = Tractor([tim], srcs)
    tractor.freezeParamsRecursive('*')
    tractor.thawPathsTo(band)
    
    R = tractor.optimize_forced_photometry(
        minsb=0, mindlnp=1.0, sky=False, fitstats=True,
        variance=True, shared_params=False, wantims=False)

    # Unpack the results and return.
    phot = fits_table()
    nm = np.array([src.getBrightness().getBand(band) for src in srcs])
    phot.set('flux_{}'.format(band), nm.astype(np.float32))
    
    return phot

def custom_coadds(onegal, galaxy=None, survey=None, radius_mosaic=None,
                  bands=('g', 'r', 'i'), nproc=1, pixscale=0.396, 
                  log=None, verbose=False):
    """Build the model and residual SDSS coadds for a single galaxy using the LS
    Tractor catalog but re-optimizing the fluxes.

    radius_mosaic in arcsec

    """
    from tractor.basics import NanoMaggies

    from legacypipe.catalog import read_fits_catalog
    from legacypipe.runbrick import _get_mod
    from legacypipe.coadds import make_coadds, write_coadd_images
    from legacypipe.survey import get_rgb, imsave_jpeg
            
    if survey is None:
        from legacypipe.survey import LegacySurveyData
        survey = LegacySurveyData()

    if galaxy is None:
        galaxy = 'galaxy'
        
    mp = multiproc(nthreads=nproc)

    brickname = custom_brickname(onegal['RA'], onegal['DEC'])
    width = np.ceil(2 * radius_mosaic / pixscale).astype('int') # [pixels]

    # Read the Tractor catalog.
    tractorfile = os.path.join(survey.output_dir, '{}-tractor.fits'.format(galaxy))
    if not os.path.isfile(tractorfile):
        print('Missing Tractor catalog {}'.format(tractorfile))
        return 0
    
    cat = fits_table(tractorfile)
    srcs = read_fits_catalog(cat, fluxPrefix='')
    print('Read {} sources from {}'.format(len(cat), tractorfile), flush=True, file=log)

    # Build a src catalog with the gri bandpasses.
    initflx = {}
    for band in bands:
        initflx.update({band: 1.0})
    
    sdss_srcs = []
    for src in srcs:
        src = src.copy()
        src.setBrightness(NanoMaggies(**initflx))
        sdss_srcs.append(src)

    print('Performing forced photometry in {}'.format(bands))
    allphot = mp.map(_forced_phot, [(galaxy, survey, sdss_srcs, band) for band in bands])

    # Build the output table (having 'flux_g', 'flux_r', and 'flux_i').
    phot = None
    for onephot in allphot:
        if phot is None:
            phot = onephot
        else:
            phot.add_columns_from(onephot)

    print(phot.flux_r/cat.flux_r)
    pdb.set_trace()

    # Custom code for dealing with centrals.
    keep = isolate_central(cat, onegal, radius_mosaic, brickwcs, width, centrals=True)

    # Build a tim for the coadd and read the srcs catalog.
    for band in ('g', 'r', 'i'):
        for src in srcs:
            src.freezeAllBut('brightness')
            src.getBrightness().freezeAllBut(tim.band)
            
    
    srcs_nocentral = np.array(srcs)[keep].tolist()

    print('Rendering model images with and without surrounding galaxies...', flush=True, file=log)
    mod = legacyhalos.misc.srcs2image(srcs, ConstantFitsWcs(brickwcs), psf_sigma=1.0)
    mod_nocentral = legacyhalos.misc.srcs2image(srcs_nocentral, ConstantFitsWcs(brickwcs), psf_sigma=1.0)


    modargs = [(tim, srcs_nocentral) for tim in newtims]
    mods_nocentral = mp.map(_get_mod, modargs)
    
    #import matplotlib.pyplot as plt ; plt.imshow(np.log10(mod), origin='lower') ; plt.savefig('junk.png')    
    #pdb.set_trace()

    # [5] Build the custom coadds, with and without the surrounding galaxies.
    print('Producing coadds...', flush=True, file=log)
    def call_make_coadds(usemods):
        return make_coadds(newtims, bands, brickwcs, mods=usemods, mp=mp,
                           callback=write_coadd_images,
                           callback_args=(survey, brickname, version_header, 
                                          newtims, brickwcs))

    # Custom coadds (all galaxies).
    if log:
        with redirect_stdout(log), redirect_stderr(log):
            C = call_make_coadds(mods)
    else:
        C = call_make_coadds(mods)

    for suffix in ('image', 'model'):
        for band in bands:
            ok = _copyfile(
                os.path.join(survey.output_dir, 'coadd', brickname[:3], 
                                   brickname, 'legacysurvey-{}-{}-{}.fits.fz'.format(
                    brickname, suffix, band)),
                os.path.join(survey.output_dir, '{}-custom-{}-{}.fits.fz'.format(galaxy, suffix, band)) )
                #os.path.join(survey.output_dir, '{}-custom-{}-{}.fits.fz'.format(galaxy, suffix, band)) )
            if not ok:
                return ok

    # Custom coadds (without the central).
    if log:
        with redirect_stdout(log), redirect_stderr(log):
            C_nocentral = call_make_coadds(mods_nocentral)
    else:
        C_nocentral = call_make_coadds(mods_nocentral)

    # Move (rename) the coadds into the desired output directory - no central.
    for suffix in np.atleast_1d('model'):
    #for suffix in ('image', 'model'):
        for band in bands:
            ok = _copyfile(
                os.path.join(survey.output_dir, 'coadd', brickname[:3], 
                                   brickname, 'legacysurvey-{}-{}-{}.fits.fz'.format(
                    brickname, suffix, band)),
                os.path.join(survey.output_dir, '{}-custom-{}-nocentral-{}.fits.fz'.format(galaxy, suffix, band)) )
                #os.path.join(survey.output_dir, '{}-custom-{}-nocentral-{}.fits.fz'.format(galaxy, suffix, band)) )
            if not ok:
                return ok
            
    if cleanup:
        shutil.rmtree(os.path.join(survey.output_dir, 'coadd'))

    # [6] Finally, build png images.
    def call_make_png(C, nocentral=False):
        rgbkwargs = dict(mnmx=(-1, 100), arcsinh=1)
        #rgbkwargs_resid = dict(mnmx=(0.1, 2), arcsinh=1)
        rgbkwargs_resid = dict(mnmx=(-1, 100), arcsinh=1)

        if nocentral:
            coadd_list = [('custom-model-nocentral', C.comods, rgbkwargs),
                          ('custom-image-central', C.coresids, rgbkwargs_resid)]
        else:
            coadd_list = [('custom-image', C.coimgs,   rgbkwargs),
                          ('custom-model', C.comods,   rgbkwargs),
                          ('custom-resid', C.coresids, rgbkwargs_resid)]

        for suffix, ims, rgbkw in coadd_list:
            rgb = get_rgb(ims, bands, **rgbkw)
            kwa = {}
            outfn = os.path.join(survey.output_dir, '{}-{}-grz.jpg'.format(galaxy, suffix))
            print('Writing {}'.format(outfn), flush=True, file=log)
            imsave_jpeg(outfn, rgb, origin='lower', **kwa)
            del rgb

    call_make_png(C, nocentral=False)
    call_make_png(C_nocentral, nocentral=True)

    return 1

def download(sample, pixscale=0.396, bands='gri', clobber=False):
    """Note that the cutout server has a maximum cutout size of 3000 pixels.
    
    montage -bordercolor white -borderwidth 1 -tile 2x2 -geometry +0+0 -resize 512 \
      NGC0628-SDSS.jpg NGC3184-SDSS.jpg NGC5194-SDSS.jpg NGC5457-SDSS.jpg chaos-montage.png

    """
    for onegal in sample:
        gal, galdir = legacyhalos.io.get_galaxy_galaxydir(onegal)
    
        size_mosaic = 2 * legacyhalos.misc.cutout_radius_kpc(pixscale=pixscale, # [pixel]
            redshift=onegal['Z'], radius_kpc=RADIUS_CLUSTER_KPC)
        print(gal, size_mosaic)

        # Individual FITS files--
        outfile = os.path.join(galdir, '{}-sdss-image-gri.fits'.format(gal))
        if os.path.exists(outfile) and clobber is False:
            print('Already downloaded {}'.format(outfile))
        else:
            cmd = 'wget -O {outfile} '
            cmd += 'http://legacysurvey.org/viewer-dev/fits-cutout?ra={ra}&dec={dec}&pixscale={pixscale}&size={size}&layer=sdss'
            cmd = cmd.format(outfile=outfile, ra=onegal['RA'], dec=onegal['DEC'],
                             pixscale=pixscale, size=size_mosaic)
            print(cmd)
            err = subprocess.call(cmd.split())
            time.sleep(1)

            # Unpack into individual bandpasses and compress.
            imgs, hdrs = fitsio.read(outfile, header=True)
            [hdrs.delete(key) for key in ('BANDS', 'BAND0', 'BAND1', 'BAND2')]
            for ii, band in enumerate(bands):
                hdr = copy.deepcopy(hdrs)
                hdr.add_record(dict(name='BAND', value=band, comment='SDSS bandpass'))
                bandfile = os.path.join(galdir, '{}-sdss-image-{}.fits.fz'.format(gal, band))
                if os.path.isfile(bandfile):
                    os.remove(bandfile)
                print('Writing {}'.format(bandfile))
                fitsio.write(bandfile, imgs[ii, :, :], header=hdr)

            pdb.set_trace()

            print('Removing {}'.format(outfile))
            os.remove(outfile)

        # Color mosaic--
        outfile = os.path.join(galdir, '{}-sdss-image-gri.jpg'.format(gal))
        if os.path.exists(outfile) and clobber is False:
            print('Already downloaded {}'.format(outfile))
        else:
            if os.path.exists(outfile) and clobber:
                os.remove(outfile) # otherwise wget will complain
            cmd = 'wget -O {outfile} '
            cmd += 'http://legacysurvey.org/viewer-dev/jpeg-cutout?ra={ra}&dec={dec}&pixscale={pixscale}&size={size}&layer=sdss'
            cmd = cmd.format(outfile=outfile, ra=onegal['RA'], dec=onegal['DEC'],
                             pixscale=pixscale, size=size_mosaic)
            print(cmd)
            err = subprocess.call(cmd.split())
            time.sleep(1)

