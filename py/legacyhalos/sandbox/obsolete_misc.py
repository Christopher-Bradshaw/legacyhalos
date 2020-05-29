"""Various obsolete code that I will eventually delete.

"""
def read_all_ccds(dr='dr9'):
    """Read the CCDs files, treating DECaLS and BASS+MzLS separately.

    """
    from astrometry.libkd.spherematch import tree_open
    #survey = LegacySurveyData()

    drdir = os.path.join(sample_dir(), dr)

    kdccds_north = []
    for camera in ('90prime', 'mosaic'):
        ccdsfile = os.path.join(drdir, 'survey-ccds-{}-{}.kd.fits'.format(camera, dr))
        ccds = tree_open(ccdsfile, 'ccds')
        print('Read {} CCDs from {}'.format(ccds.n, ccdsfile))
        kdccds_north.append((ccdsfile, ccds))

    ccdsfile = os.path.join(drdir, 'survey-ccds-decam-{}.kd.fits'.format(dr))
    ccds = tree_open(ccdsfile, 'ccds')
    print('Read {} CCDs from {}'.format(ccds.n, ccdsfile))
    kdccds_south = (ccdsfile, ccds)

    return kdccds_north, kdccds_south

def get_run_ccds(onegal, radius_mosaic, pixscale, log=None): # kdccds_north, kdccds_south, log=None):
    """Determine the "run", i.e., determine whether we should use the BASS+MzLS CCDs
    or the DECaLS CCDs file when running the pipeline.

    """
    from astrometry.util.fits import fits_table, merge_tables
    from astrometry.util.util import Tan
    from astrometry.libkd.spherematch import tree_search_radec
    from legacypipe.survey import ccds_touching_wcs
    import legacyhalos.coadds
    
    ra, dec = onegal['RA'], onegal['DEC']
    if dec < 25:
        run = 'decam'
    elif dec > 40:
        run = '90prime-mosaic'
    else:
        width = legacyhalos.coadds._mosaic_width(radius_mosaic, pixscale)
        wcs = Tan(ra, dec, width/2+0.5, width/2+0.5,
                  -pixscale/3600.0, 0.0, 0.0, pixscale/3600.0, 
                  float(width), float(width))

        # BASS+MzLS
        TT = []
        for fn, kd in kdccds_north:
            I = tree_search_radec(kd, ra, dec, 1.0)
            if len(I) == 0:
                continue
            TT.append(fits_table(fn, rows=I))
        if len(TT) == 0:
            inorth = []
        else:
            ccds = merge_tables(TT, columns='fillzero')
            inorth = ccds_touching_wcs(wcs, ccds)
        
        # DECaLS
        fn, kd = kdccds_south
        I = tree_search_radec(kd, ra, dec, 1.0)
        if len(I) > 0:
            ccds = fits_table(fn, rows=I)
            isouth = ccds_touching_wcs(wcs, ccds)
        else:
            isouth = []

        if len(inorth) > len(isouth):
            run = '90prime-mosaic'
        else:
            run = 'decam'
        print('RA, Dec={:.6f}, {:.6f}: run={} ({} north CCDs, {} south CCDs).'.format(
            ra, dec, run, len(inorth), len(isouth)), flush=True, file=log)

    return run

def check_and_read_ccds(galaxy, survey, debug=False, logfile=None):
    """Read the CCDs file generated by the pipeline coadds step.

    """
    ccdsfile_south = os.path.join(survey.output_dir, '{}-ccds-south.fits'.format(galaxy))
    ccdsfile_north = os.path.join(survey.output_dir, '{}-ccds-north.fits'.format(galaxy))
    #ccdsfile_south = os.path.join(survey.output_dir, '{}-ccds-decam.fits'.format(galaxy))
    #ccdsfile_north = os.path.join(survey.output_dir, '{}-ccds-90prime-mosaic.fits'.format(galaxy))
    if os.path.isfile(ccdsfile_south):
        ccdsfile = ccdsfile_south
    elif os.path.isfile(ccdsfile_north):
        ccdsfile = ccdsfile_north
    else:
        if debug:
            print('CCDs file {} not found.'.format(ccdsfile_south), flush=True)
            print('CCDs file {} not found.'.format(ccdsfile_north), flush=True)
            print('ERROR: galaxy {}; please check the logfile.'.format(galaxy), flush=True)
        else:
            with open(logfile, 'w') as log:
                print('CCDs file {} not found.'.format(ccdsfile_south), flush=True, file=log)
                print('CCDs file {} not found.'.format(ccdsfile_north), flush=True, file=log)
                print('ERROR: galaxy {}; please check the logfile.'.format(galaxy), flush=True, file=log)
        return False
    survey.ccds = survey.cleanup_ccds_table(fits_table(ccdsfile))

    # Check that coadds in all three grz bandpasses were generated in the
    # previous step.
    if ('g' not in survey.ccds.filter) or ('r' not in survey.ccds.filter) or ('z' not in survey.ccds.filter):
        if debug:
            print('Missing grz coadds...skipping.', flush=True)
            print('ERROR: galaxy {}; please check the logfile.'.format(galaxy), flush=True)
        else:
            with open(logfile, 'w') as log:
                print('Missing grz coadds...skipping.', flush=True, file=log)
                print('ERROR: galaxy {}; please check the logfile.'.format(galaxy), flush=True, file=log)
        return False
    return True

def _write_ellipsefit(galaxy, galaxydir, ellipsefit, filesuffix='', galaxyid='',
                     verbose=False, use_pickle=False):
    """Write out an ASDF file based on the output of
    legacyhalos.ellipse.ellipse_multiband..

    use_pickle - write an old-style pickle file

    OBSOLETE - we now use FITS

    """
    import pickle
    from astropy.io import fits
    from asdf import fits_embed
    #import asdf
    
    if use_pickle:
        suff = '.p'
    else:
        suff = '.fits'
        #suff = '.asdf'

    if galaxyid.strip() == '':
        galid = ''
    else:
        galid = '-{}'.format(galaxyid)
    if filesuffix.strip() == '':
        fsuff = ''
    else:
        fsuff = '-{}'.format(filesuffix)
        
    ellipsefitfile = os.path.join(galaxydir, '{}{}{}-ellipse{}'.format(galaxy, fsuff, galid, suff))
        
    if verbose:
        print('Writing {}'.format(ellipsefitfile))
    if use_pickle:
        with open(ellipsefitfile, 'wb') as ell:
            pickle.dump(ellipsefit, ell, protocol=2)
    else:
        pdb.set_trace()
        hdu = fits.HDUList()
        af = fits_embed.AsdfInFits(hdu, ellipsefit)
        af.write_to(ellipsefitfile)
        #af = asdf.AsdfFile(ellipsefit)
        #af.write_to(ellipsefitfile)

def _read_ellipsefit(galaxy, galaxydir, filesuffix='', galaxyid='', verbose=True, use_pickle=False):
    """Read the output of write_ellipsefit.

    OBSOLETE - we now use FITS

    """
    import pickle
    import asdf
    
    if use_pickle:
        suff = '.p'
    else:
        suff = '.asdf'
    
    if galaxyid.strip() == '':
        galid = ''
    else:
        galid = '-{}'.format(galaxyid)
    if filesuffix.strip() == '':
        fsuff = ''
    else:
        fsuff = '-{}'.format(filesuffix)

    ellipsefitfile = os.path.join(galaxydir, '{}{}{}-ellipse{}'.format(galaxy, fsuff, galid, suff))
        
    try:
        if use_pickle:
            with open(ellipsefitfile, 'rb') as ell:
                ellipsefit = pickle.load(ell)
        else:
            #with asdf.open(ellipsefitfile) as af:
            #    ellipsefit = af.tree
            ellipsefit = asdf.open(ellipsefitfile)
    except:
        #raise IOError
        if verbose:
            print('File {} not found!'.format(ellipsefitfile))
        ellipsefit = dict()

    return ellipsefit

def write_mgefit(galaxy, galaxydir, mgefit, band='r', verbose=False):
    """Pickle an XXXXX object (see, e.g., ellipse.mgefit_multiband).

    """
    mgefitfile = os.path.join(galaxydir, '{}-mgefit.p'.format(galaxy))
    if verbose:
        print('Writing {}'.format(mgefitfile))
    with open(mgefitfile, 'wb') as mge:
        pickle.dump(mgefit, mge, protocol=2)

def read_mgefit(galaxy, galaxydir, verbose=True):
    """Read the output of write_mgefit."""

    mgefitfile = os.path.join(galaxydir, '{}-mgefit.p'.format(galaxy))
    try:
        with open(mgefitfile, 'rb') as mge:
            mgefit = pickle.load(mge)
    except:
        #raise IOError
        if verbose:
            print('File {} not found!'.format(mgefitfile))
        mgefit = dict()

    return mgefit

