;+
; NAME:
;   LEGACYHALOS_ISEDFIT
;
; PURPOSE:
;   Use iSEDfit to compute stellar masses for the various legacyhalos samples.
;
; INPUTS:
;   At least one of /LSPHOT_DR6_DR7, /LHPHOT, /SDSSPHOT_DR14 must be set.
;
; OPTIONAL INPUTS:
;   thissfhgrid
;
; KEYWORD PARAMETERS:
;   lsphot_dr6_dr7
;   lhphot
;   sdssphot_dr14
;   sdssphot_upenn
;   redmapper_upenn
;   write_paramfile
;   build_grids
;   model_photometry
;   isedfit
;   kcorrect
;   qaplot_sed
;   gather_results
;   clobber
;
; OUTPUTS:
;
; COMMENTS:
;   See https://github.com/moustakas/legacyhalos for more info about the
;   fitting. 
;
; MODIFICATION HISTORY:
;   J. Moustakas, 2017 Dec 27, Siena
;   jm18jul16siena - fit first-pass legacyhalos photometry 
;   jm18aug17siena - update to latest sample and data model 
;
; Copyright (C) 2017-2018, John Moustakas
; 
; This program is free software; you can redistribute it and/or modify 
; it under the terms of the GNU General Public License as published by 
; the Free Software Foundation; either version 2 of the License, or
; (at your option) any later version. 
; 
; This program is distributed in the hope that it will be useful, but 
; WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
; General Public License for more details. 
;-

function lhphot_version
; v1.0 - original effort    
    ver = 'v1.0'
return, ver
end    

function get_pofm, prefix, outprefix, isedfit_rootdir, $
  thissfhgrid=thissfhgrid, kcorr=kcorr
; read the marginalized posterior on stellar mass, pack it into the iSEDfit
; structure, read the k-corrections and return

    isedfit_dir = isedfit_rootdir+'isedfit_'+prefix+'/'
    montegrids_dir = isedfit_rootdir+'montegrids_'+prefix+'/'
    isedfit_paramfile = isedfit_dir+prefix+'_paramfile.par'

    fp = isedfit_filepaths(read_isedfit_paramfile(isedfit_paramfile,$
      thissfhgrid=thissfhgrid),isedfit_dir=isedfit_dir,band_shift=0.1,$
      montegrids_dir=montegrids_dir,outprefix=outprefix)
    
    npofm = 21 ; number of posterior samplings on stellar mass
    ngal = sxpar(headfits(fp.isedfit_dir+fp.isedfit_outfile+'.gz',ext=1), 'NAXIS2')

    nperchunk = ngal            ; 50000
    nchunk = ceil(ngal/float(nperchunk))
    
    for ii = 0, nchunk-1 do begin
       print, format='("Working on chunk ",I0,"/",I0)', ii+1, nchunk
       these = lindgen(nperchunk)+ii*nperchunk
       these = these[where(these lt ngal)]
;      these = these[0:99] ; test!

       delvarx, post
       outphot1 = read_isedfit(isedfit_paramfile,isedfit_dir=isedfit_dir,$
         montegrids_dir=montegrids_dir,outprefix=outprefix,index=these,$
         isedfit_post=post,thissfhgrid=thissfhgrid)
       outphot1 = struct_trimtags(struct_trimtags(outphot1,except='*HB*'),except='*HA*')
             
       if ii eq 0 then begin
          outphot = replicate(outphot1[0], ngal)
          outphot = struct_addtags(outphot, replicate({pofm: fltarr(npofm),$
            pofm_bins: fltarr(npofm)},ngal))
       endif
       outphot[these] = im_struct_assign(outphot1, outphot[these], /nozero)

       for jj = 0, n_elements(these)-1 do begin
          mn = min(post[jj].mstar)
          mx = max(post[jj].mstar)
          dm = (mx - mn) / (npofm - 1)

          pofm = im_hist1d(post[jj].mstar,binsize=dm,$
            binedge=0,obin=pofm_bins)
          outphot[these[jj]].pofm = pofm / im_integral(pofm_bins, pofm) ; normalize
          outphot[these[jj]].pofm_bins = pofm_bins
       endfor
    endfor             

    kcorrfile = fp.isedfit_dir+fp.kcorr_outfile+'.gz'
    print, 'Reading '+kcorrfile
    kcorr = mrdfits(kcorrfile,1)
          
return, outphot
end

pro legacyhalos_isedfit, lsphot_dr6_dr7=lsphot_dr6_dr7, lhphot=lhphot, $
  sdssphot_dr14=sdssphot_dr14, sdssphot_upenn=sdssphot_upenn, $
  redmapper_upenn=redmapper_upenn, $  
  write_paramfile=write_paramfile, build_grids=build_grids, model_photometry=model_photometry, $
  isedfit=isedfit, kcorrect=kcorrect, qaplot_sed=qaplot_sed, thissfhgrid=thissfhgrid, $
  gather_results=gather_results, clobber=clobber, satellites=satellites

; echo "legacyhalos_isedfit, /lsphot_dr6_dr7, /isedfit, /kcorrect, /qaplot_sed, /cl" | /usr/bin/nohup idl > lsphot-dr6-dr7.log 2>&1 &
; echo "legacyhalos_isedfit, /lsphot_dr6_dr7, /write_param, /build_grids, /model_phot, /isedfit, /kcorrect, thissfhgrid=2, /cl" | /usr/bin/nohup idl > lsphot-dr6-dr7-sfhgrid02.log 2>&1 &
; echo "legacyhalos_isedfit, /sdssphot_dr14, /write_param, /build_grids, /model_phot, /isedfit, /kcorrect, /cl" | /usr/bin/nohup idl > sdssphot-dr14.log 2>&1 &

    legacyhalos_dir = getenv('LEGACYHALOS_DIR')

    if keyword_set(lsphot_dr6_dr7) eq 0 and keyword_set(lhphot) eq 0 and $
      keyword_set(sdssphot_dr14) eq 0 and keyword_set(sdssphot_upenn) eq 0 and $
      keyword_set(redmapper_upenn) eq 0 and keyword_set(gather_results) eq 0 then begin
       splog, 'Choose one of /LSPHOT_DR6_DR7, /LHPHOT, /SDSSPHOT_DR14, /SDSSPHOT_UPENN, or /REDMAPPER_UPENN'
       return       
    endif

    if n_elements(thissfhgrid) eq 0 then begin
       splog, 'THISSFHGRID is a required input!'
       return
    endif
    sfhgridstring = 'sfhgrid'+string(thissfhgrid,format='(I2.2)')
    
; directories and prefixes for each dataset
    if keyword_set(lsphot_dr6_dr7) then begin
       prefix = 'lsphot'
       outprefix = 'lsphot_dr6_dr7'
    endif
    if keyword_set(lhphot) then begin
       version = lhphot_version()
       prefix = 'lsphot'
       outprefix = 'lhphot_'+version
    endif
    if keyword_set(sdssphot_dr14) then begin
       prefix = 'sdssphot'
       outprefix = 'sdssphot_dr14'
    endif
    if keyword_set(sdssphot_upenn) then begin
       prefix = 'sdssphot'
       outprefix = 'sdssphot_upenn'
    endif
    if keyword_set(redmapper_upenn) then begin
       prefix = 'sdssphot'
       outprefix = 'redmapper_upenn'
    endif

    if keyword_set(satellites) then begin
       nsatchunk = 20
       sampleprefix = 'satellites'
    endif else begin
       sampleprefix = 'centrals'
    endelse
    
    isedfit_rootdir = getenv('IM_WORK_DIR')+'/projects/legacyhalos/isedfit/'
    
    isedfit_dir = isedfit_rootdir+'isedfit_'+prefix+'/'
    montegrids_dir = isedfit_rootdir+'montegrids_'+prefix+'/'
    isedfit_paramfile = isedfit_dir+prefix+'_paramfile.par'

    spawn, ['mkdir -p '+isedfit_dir], /sh
    spawn, ['mkdir -p '+montegrids_dir], /sh

; --------------------------------------------------
; gather the results and write out the final stellar mass catalog, including the
; posterior probability on stellar mass 
    if keyword_set(gather_results) then begin

       if keyword_set(lsphot_dr6_dr7) then begin
          lsphot = get_pofm(prefix,outprefix,isedfit_rootdir,$
            thissfhgrid=thissfhgrid,kcorr=lsphot_kcorr)

          outfile = legacyhalos_dir+'/sample/'+sampleprefix+'-'+sfhgridstring+'-lsphot-dr6-dr7.fits'

          splog, 'Writing '+outfile
          mwrfits, lsphot, outfile, /create
          mwrfits, lsphot_kcorr, outfile
	
          hdr = headfits(outfile,ext=1)
          sxaddpar, hdr, 'EXTNAME', 'LSPHOT-ISEDFIT'
          modfits, outfile, 0, hdr, exten_no=1
	
          hdr = headfits(outfile,ext=2)
          sxaddpar, hdr, 'EXTNAME', 'LSPHOT-KCORR'
          modfits, outfile, 0, hdr, exten_no=2
       endif

       if keyword_set(sdssphot_dr14) then begin
          sdssphot = get_pofm(prefix,outprefix,isedfit_rootdir,$
            thissfhgrid=thissfhgrid,kcorr=sdssphot_kcorr)
          
          outfile = legacyhalos_dir+'/sample/'+sampleprefix+'-'+sfhgridstring+'-sdssphot-dr14.fits'
          splog, 'Writing '+outfile
          mwrfits, sdssphot, outfile, /create
          mwrfits, sdssphot_kcorr, outfile

          hdr = headfits(outfile,ext=1)
          sxaddpar, hdr, 'EXTNAME', 'SDSSPHOT-ISEDFIT'
          modfits, outfile, 0, hdr, exten_no=1

          hdr = headfits(outfile,ext=2)
          sxaddpar, hdr, 'EXTNAME', 'SDSSPHOT-KCORR'
          modfits, outfile, 0, hdr, exten_no=2
       endif

       stop
       
; upenn subsample       
       print, 'HACK!!!!!!!!!!!!!!'
       print, 'Rewrite the mendel stellar mass results.'
       upenn = mrdfits(legacyhalos_dir+'/redmapper-upenn.fits', 3)
       upenn_radec = mrdfits(legacyhalos_dir+'/redmapper-upenn.fits', 1, columns=['RA', 'DEC'])

;      upenn = mrdfits(isedfit_rootdir+'isedfit_sdssphot/'+$
;        'redmapper_upenn_fsps_v2.4_miles_chab_charlot_sfhgrid01.fits.gz',1)
;      upenn_kcorr = mrdfits(isedfit_rootdir+'isedfit_sdssphot/'+$
;        'redmapper_upenn_fsps_v2.4_miles_chab_charlot_sfhgrid01_kcorr.z0.1.fits.gz',1)

       lhphot = mrdfits(isedfit_rootdir+'isedfit_lsphot/'+$
         'lhphot_v1.0_fsps_v2.4_miles_chab_charlot_sfhgrid01.fits.gz',1)

; match to upenn       
       spherematch, upenn_radec.ra, upenn_radec.dec, lhphot.ra, lhphot.dec, 1D/3600, m1, m2, d12
       srt = sort(m2) & m1 = m1[srt] & m2 = m2[srt]
       upenn = upenn[m1]
;      upenn_kcorr = upenn_kcorr[m1]
       
; match to lsphot
       spherematch, lsphot.ra, lsphot.dec, lhphot.ra, lhphot.dec, 1D/3600, m1, m2, d12
       srt = sort(m2) & m1 = m1[srt] & m2 = m2[srt]
       lsphot = lsphot[m1]
       lsphot_kcorr = lsphot_kcorr[m1]
       
; match to sdssphot
       spherematch, sdssphot.ra, sdssphot.dec, lhphot.ra, lhphot.dec, 1D/3600, m1, m2, d12
       srt = sort(m2) & m1 = m1[srt] & m2 = m2[srt]
       sdssphot = sdssphot[m1]
       sdssphot_kcorr = sdssphot_kcorr[m1]
       
       outfile = legacyhalos_dir+'/redmapper-upenn-isedfit.fits'
       mwrfits, upenn, outfile, /create
;      mwrfits, upenn_kcorr, outfile
       mwrfits, lhphot, outfile
       mwrfits, lsphot, outfile
       mwrfits, sdssphot, outfile

       ee = 1
       hdr = headfits(outfile,ext=ee)
       sxaddpar, hdr, 'EXTNAME', 'UPENN'
       modfits, outfile, 0, hdr, exten_no=ee

       print, 'Leave off my isedfit masses.'
;      hdr = headfits(outfile,ext=ee)
;      sxaddpar, hdr, 'EXTNAME', 'UPENN-ISEDFIT'
;      modfits, outfile, 0, hdr, exten_no=ee
       
       print, 'HACK!!  Leave off K-correct'
;      hdr = headfits(outfile,ext=2)
;      sxaddpar, hdr, 'EXTNAME', 'UPENN-KCORR'
;      modfits, outfile, 0, hdr, exten_no=2

       ee = 2
       hdr = headfits(outfile,ext=ee)
       sxaddpar, hdr, 'EXTNAME', 'LHPHOT-ISEDFIT'
       modfits, outfile, 0, hdr, exten_no=ee

       ee = 3
       hdr = headfits(outfile,ext=ee)
       sxaddpar, hdr, 'EXTNAME', 'LSPHOT-ISEDFIT'
       modfits, outfile, 0, hdr, exten_no=ee

       ee = 4
       hdr = headfits(outfile,ext=ee)
       sxaddpar, hdr, 'EXTNAME', 'SDSSPHOT-ISEDFIT'
       modfits, outfile, 0, hdr, exten_no=ee
       return
    endif

; --------------------------------------------------
; define the filters and the redshift ranges
    if keyword_set(lsphot_dr6_dr7) or keyword_set(lhphot) then begin
       filterlist = [legacysurvey_filterlist(), wise_filterlist(/short)]
       zminmax = [0.05,0.6]
       nzz = 61
    endif
    if keyword_set(sdssphot_dr14) or keyword_set(redmapper_upenn) then begin
       filterlist = [sdss_filterlist(), wise_filterlist(/short)]
       zminmax = [0.05,0.6]
       nzz = 61
    endif
    if keyword_set(sdssphot_upenn) then begin
       filterlist = [sdss_filterlist(), wise_filterlist(/short)] ; most of these will be zeros
       zminmax = [0.05,0.4]
       nzz = 41
    endif

    absmag_filterlist = [sdss_filterlist(), legacysurvey_filterlist()]
    band_shift = 0.1
    
; --------------------------------------------------
; DR6/DR7 LegacySurvey (grz) + unWISE W1 & W2    
    if keyword_set(lsphot_dr6_dr7) then begin
       cat = mrdfits(legacyhalos_dir+'/sample/legacyhalos-'+sampleprefix+'-dr6-dr7.fits', 1)
       ngal = n_elements(cat)

       ra = cat.ra
       dec = cat.dec
       zobj = cat.z
       
       factor = 1D-9 / transpose([ [cat.mw_transmission_g], [cat.mw_transmission_r], $
         [cat.mw_transmission_z] ])
       dmaggies = float(transpose([ [cat.flux_g], [cat.flux_r], [cat.flux_z] ]) * factor)
       divarmaggies = float(transpose([ [cat.flux_ivar_g], [cat.flux_ivar_r], $
         [cat.flux_ivar_z] ]) / factor^2)
       
       factor = 1D-9 / transpose([ [cat.mw_transmission_w1], [cat.mw_transmission_w2] ])
       wmaggies = float(transpose([ [cat.flux_w1], [cat.flux_w2] ]) * factor)
       wivarmaggies = float(transpose([ [cat.flux_ivar_w1], [cat.flux_ivar_w2] ]) / factor^2)

       maggies = [dmaggies, wmaggies]
       ivarmaggies = [divarmaggies, wivarmaggies]

; mask out wonky unWISE photometry
       snr = maggies*sqrt(ivarmaggies)
       ww = where(abs(snr[3,*]) gt 1e3) & ivarmaggies[3,ww] = 0
       ww = where(abs(snr[4,*]) gt 1e3) & ivarmaggies[4,ww] = 0

; add minimum calibration uncertainties (in quadrature) to grzW1W2; see
; [desi-targets 2084]
       k_minerror, maggies, ivarmaggies, [0.003,0.003,0.006,0.005,0.02]
    endif
    
; --------------------------------------------------
; custom LegacySurvey (grz) + unWISE W1 & W2    
    if keyword_set(lhphot) then begin
       cat = mrdfits(legacyhalos_dir+'/legacyhalos-results.fits', 'LHPHOT')

       ra = cat.ra
       dec = cat.dec
       zobj = cat.z

       factor = 1D-9 / transpose([ [cat.mw_transmission_g], [cat.mw_transmission_r], $
         [cat.mw_transmission_z] ])
       dmaggies = float(transpose([ [cat.flux_g], [cat.flux_r], [cat.flux_z] ]) * factor)
       divarmaggies = float(transpose([ [cat.flux_ivar_g], [cat.flux_ivar_r], $
         [cat.flux_ivar_z] ]) / factor^2)
       
       factor = 1D-9 / transpose([ [cat.mw_transmission_w1], [cat.mw_transmission_w2] ])
       wmaggies = float(transpose([ [cat.flux_w1], [cat.flux_w2] ]) * factor)
       wivarmaggies = float(transpose([ [cat.flux_ivar_w1], [cat.flux_ivar_w2] ]) / factor^2)

       maggies = [dmaggies, wmaggies]
       ivarmaggies = [divarmaggies, wivarmaggies]

; add minimum uncertainties to grzW1W2
       k_minerror, maggies, ivarmaggies, [0.02,0.02,0.02,0.005,0.02]
    endif

; --------------------------------------------------
; SDSS ugriz + forced WISE photometry from Lang & Schlegel    
    if keyword_set(sdssphot_dr14) then begin
       cat = mrdfits(legacyhalos_dir+'/sample/legacyhalos-'+sampleprefix+'-dr6-dr7.fits', 1)
       ngal = n_elements(cat)

       ra = cat.ra
       dec = cat.dec
       zobj = cat.z
       
       ratio = cat.cmodelmaggies[2,*]/cat.modelmaggies[2,*]
       factor = 1D-9 * rebin(ratio, 5, ngal) * 10D^(0.4*cat.extinction)
       smaggies = cat.modelmaggies * factor
       sivarmaggies = cat.modelmaggies_ivar / factor^2

       vega2ab = rebin([2.699,3.339],2,ngal) ; Vega-->AB from http://legacysurvey.org/dr5/description/#photometry
       glactc, cat.ra, cat.dec, 2000.0, gl, gb, 1, /deg
       ebv = rebin(reform(dust_getval(gl,gb,/interp,/noloop),1,ngal),2,ngal)
       coeff = rebin(reform([0.184,0.113],2,1),2,ngal) ; Galactic extinction coefficients from http://legacysurvey.org/dr5/catalogs

       factor = 1D-9 * 10^(0.4*coeff*ebv)*10^(-0.4*vega2ab)
       wmaggies = float(cat.wise_nanomaggies * factor)
       wivarmaggies = float(cat.wise_nanomaggies_ivar / factor^2)
       
       maggies = [smaggies, wmaggies]
       ivarmaggies = [sivarmaggies, wivarmaggies]
       
; add minimum uncertainties to ugrizW1W2
       k_minerror, maggies, ivarmaggies, [0.05,0.02,0.02,0.02,0.03,0.005,0.02]
    endif

; --------------------------------------------------
; SDSS ugriz
    if keyword_set(redmapper_upenn) then begin
       rm = mrdfits(legacyhalos_dir+'/redmapper-upenn.fits', 'REDMAPPER')
       cat = mrdfits(legacyhalos_dir+'/redmapper-upenn.fits', 'SDSSPHOT')
       ngal = n_elements(cat)

       ra = rm.ra
       dec = rm.dec
       zobj = rm.z
       
       ratio = cat.cmodelmaggies[2,*]/cat.modelmaggies[2,*]
       factor = 1D-9 * rebin(ratio, 5, ngal) * 10D^(0.4*cat.extinction)
       smaggies = cat.modelmaggies * factor
       sivarmaggies = cat.modelmaggies_ivar / factor^2

       maggies = [smaggies, fltarr(2,ngal)]
       ivarmaggies = [sivarmaggies, fltarr(2,ngal)]
       
       k_minerror, maggies, ivarmaggies, [0.05,0.02,0.02,0.02,0.03,0.0,0.0]
    endif

; --------------------------------------------------
; UPenn-PhotDec gri SDSS photometry
    if keyword_set(sdssphot_upenn) then begin
       rm = mrdfits(legacyhalos_dir+'/legacyhalos-parent-upenn.fits', 'REDMAPPER')
       cat = mrdfits(legacyhalos_dir+'/legacyhalos-parent-upenn.fits', 'UPENN')
       ngal = n_elements(cat)

       ra = rm.ra
       dec = rm.dec
       zobj = rm.z
       
       splog, 'Write some photometry code here!'
       stop
    endif

; --------------------------------------------------
; write the parameter file
    if keyword_set(write_paramfile) then begin
; SFHGRID01 - general SFH + dust, no emission lines
       write_isedfit_paramfile, params=params, isedfit_dir=isedfit_dir, $
         prefix=prefix, filterlist=filterlist, spsmodels='fsps_v2.4_miles', $
         imf='chab', redcurve='charlot', igm=0, zminmax=zminmax, nzz=nzz, $
         nmodel=25000L, age=[0.1,13.0], tau=[0.0,6], Zmetal=[0.004,0.03], $
         /delayed, nebular=0, clobber=clobber, sfhgrid=1
; SFHGRID02 - no dust, no emission lines
       write_isedfit_paramfile, params=params, isedfit_dir=isedfit_dir, $
         prefix=prefix, filterlist=filterlist, spsmodels='fsps_v2.4_miles', $
         imf='chab', redcurve='none', igm=0, zminmax=zminmax, nzz=nzz, $
         nmodel=25000L, age=[0.1,13.0], tau=[0.0,6], Zmetal=[0.004,0.03], $
         AV=[0,0], /delayed, nebular=0, clobber=clobber, sfhgrid=2, /append
    endif

;   splog, 'HACK!!'
;   index = lindgen(50)
;   outprefix = 'test'
;   jj = mrdfits('lsphot_dr6_dr7_fsps_v2.4_miles_chab_charlot_sfhgrid01.fits.gz',1)
;   index = where(jj.mstar lt 0)

; --------------------------------------------------
; build the Monte Carlo grids    
    if keyword_set(build_grids) then begin
       isedfit_montegrids, isedfit_paramfile, isedfit_dir=isedfit_dir, $
         montegrids_dir=montegrids_dir, thissfhgrid=thissfhgrid, clobber=clobber
    endif

; --------------------------------------------------
; calculate the model photometry 
    if keyword_set(model_photometry) then begin
       isedfit_models, isedfit_paramfile, isedfit_dir=isedfit_dir, $
         montegrids_dir=montegrids_dir, thissfhgrid=thissfhgrid, $
         clobber=clobber
    endif

; --------------------------------------------------
; fit!
    if keyword_set(isedfit) then begin
       if keyword_set(satellites) then begin
          print('Ridiculously hard-coding ngal here to speed things up!')
          ngal = 6682618L 
          chunksize = ceil(ngal/float(nsatchunk))
          if n_elements(firstchunk) eq 0 then firstchunk = 0
          if n_elements(lastchunk) eq 0 then lastchunk = nsatchunk-1

          for ii = firstchunk, lastchunk do begin
             splog, 'Working on CHUNK '+strtrim(ii,2)+', '+strtrim(lastchunk,2)
             splog, im_today()
             t0 = systime(1)
             outprefix = 'redmapper_chunk'+string(ii,format='(I3.3)')
             these = lindgen(chunksize)+ii*chunksize
             these = these[where(these lt ngal)]
             these = these[0:99] ; test!

             phot = mrdfits(redmapper_dir+'catalogs/redmapper_'+ver+'_phot.fits.gz',1,rows=these)
             isedfit, isedfit_paramfile, maggies, ivarmaggies, zobj, ra=ra, $
               dec=dec, isedfit_dir=isedfit_dir, thissfhgrid=thissfhgrid, $
               clobber=clobber, index=index, outprefix=outprefix
          endfor
       endif else begin
          isedfit, isedfit_paramfile, maggies, ivarmaggies, zobj, ra=ra, $
            dec=dec, isedfit_dir=isedfit_dir, thissfhgrid=thissfhgrid, $
            clobber=clobber, index=index, outprefix=outprefix
       endelse
    endif 

; --------------------------------------------------
; compute K-corrections
    if keyword_set(kcorrect) then begin
       isedfit_kcorrect, isedfit_paramfile, isedfit_dir=isedfit_dir, $
         montegrids_dir=montegrids_dir, thissfhgrid=thissfhgrid, $
         absmag_filterlist=absmag_filterlist, band_shift=band_shift, $
         clobber=clobber, index=index, outprefix=outprefix
    endif 

; --------------------------------------------------
; generate spectral energy distribution (SED) QAplots
    if keyword_set(qaplot_sed) then begin
       these = lindgen(50)
       isedfit_qaplot_sed, isedfit_paramfile, isedfit_dir=isedfit_dir, $
         montegrids_dir=montegrids_dir, outprefix=outprefix, thissfhgrid=thissfhgrid, $
         clobber=clobber, index=these, /xlog
    endif

    
return
end
