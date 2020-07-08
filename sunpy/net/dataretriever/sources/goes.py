# Author: Rishabh Sharma <rishabh.sharma.gunner@gmail.com>
# This module was developed under funding provided by
# Google Summer of Code 2014

from datetime import datetime
from collections import OrderedDict

import astropy.units as u

from sunpy import config
from sunpy.net import attrs as a
from sunpy.net.dataretriever import GenericClient, QueryResponse
from sunpy.time import TimeRange
from sunpy.util.scraper import Scraper

TIME_FORMAT = config.get("general", "time_format")

__all__ = ["XRSClient", "SUVIClient"]


class XRSClient(GenericClient):
    """
    Provides access to the GOES XRS fits files archive.

    Searches data hosted by the `Solar Data Analysis Center <https://umbra.nascom.nasa.gov/goes/fits/>`__.

    Examples
    --------
    >>> from sunpy.net import Fido, attrs as a
    >>> results = Fido.search(a.Time("2016/1/1", "2016/1/2"),
    ...                       a.Instrument.xrs)  #doctest: +REMOTE_DATA
    >>> results  #doctest: +REMOTE_DATA
    <sunpy.net.fido_factory.UnifiedResponse object at ...>
    Results from 1 Provider:
    <BLANKLINE>
    4 Results from the XRSClient:
         Start Time           End Time      Instrument ... Provider SatelliteNumber
    ------------------- ------------------- ---------- ... -------- ---------------
    2016-01-01 00:00:00 2016-01-01 23:59:59        XRS ...     SDAC              13
    2016-01-02 00:00:00 2016-01-02 23:59:59        XRS ...     SDAC              13
    2016-01-01 00:00:00 2016-01-01 23:59:59        XRS ...     SDAC              15
    2016-01-02 00:00:00 2016-01-02 23:59:59        XRS ...     SDAC              15
    <BLANKLINE>
    <BLANKLINE>

    """
    baseurl = r'https://umbra.nascom.nasa.gov/goes/fits/%Y/go(\d){2}(\d){6,8}\.fits'
    pattern = '{}/fits/{year:4d}/go{SatelliteNumber:02d}{}{month:2d}{day:2d}.fits'

    @classmethod
    def _attrs_module(cls):
        return 'goes', 'sunpy.net.dataretriever.attrs.goes'

    @classmethod
    def register_values(cls):
        from sunpy.net import attrs
        goes_number = [2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        adict = {attrs.Instrument: [
            ("GOES", "The Geostationary Operational Environmental Satellite Program."),
            ("XRS", "GOES X-ray Flux")],
            attrs.goes.SatelliteNumber: [(str(x), f"GOES Satellite Number {x}") for x in goes_number],
            attrs.Source: [('NASA', 'The National Aeronautics and Space Administration.')],
            attrs.Physobs: [('irradiance', 'the flux of radiant energy per unit area.')],
            attrs.Provider: [('SDAC', 'The Solar Data Analysis Center.')]}
        return adict


class SUVIClient(GenericClient):
    """
    Provides access to data from the GOES Solar Ultraviolet Imager (SUVI).

    SUVI data are provided by NOAA at the following url
    https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/
    The SUVI instrument was first included on GOES-16. It produces level-1b as
    well as level-2 data products. Level-2 data products are a weighted average
    of level-1b product files and therefore provide higher imaging dynamic
    range than individual images. The exposure time of level 1b images range
    from 1 s to 0.005 s. SUVI supports the following wavelengths;
    94, 131, 171, 195, 284, 304 angstrom. If no wavelength is specified, images
    from all wavelengths are returned.

    Note
    ----
    GOES-16 began providing regular level-1b data on 2018-06-01.  At the time
    of writing, SUVI on GOES-17 is operational but currently does not provide
    Level-2 data.
    """
    baseurl1b = (r'https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes'
                 r'{SatelliteNumber}/l1b/suvi-l1b-{elem:2}{wave:03}/%Y/%m/%d/OR_SUVI-L1b.*\.fits.gz')
    pattern1b = ('{}/goes/goes{SatelliteNumber:2d}/l{Level:2w}/suvi-l1b-{}{Wavelength:03d}/'
                 '{year:4d}/{month:2d}/{day:2d}/{}_s{:7d}{hour:2d}{minute:2d}{second:2d}'
                 '{:1d}_e{:7d}{ehour:2d}{eminute:2d}{esecond:2d}{:1d}_{}')
    baseurl2 = (r'https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes{SatelliteNumber}/'
                r'l2/data/suvi-l2-ci{wave:03}/%Y/%m/%d/dr_suvi-l2-ci{wave:03}_g{SatelliteNumber}_s%Y%m%dT%H%M%SZ_.*\.fits')
    pattern2 = ('{}/goes/goes{SatelliteNumber:2d}/{}/dr_suvi-l{Level}-ci{Wavelength:03d}_g{SatelliteNumber:2d}_s'
                '{year:4d}{month:2d}{day:2d}T{hour:2d}{minute:2d}{second:2d}Z_e'
                '{eyear:4d}{emonth:2d}{eday:2d}T{ehour:2d}{eminute:2d}{esecond:2d}Z_{}')
    optional = {a.Wavelength, a.Source, a.Provider, a.Level, a.Physobs}

    def pre_search_hook(cls, *args, **kwargs):
        matchdict = cls._get_match_dict(*args, **kwargs)
        return cls.baseurl1b, cls.pattern1b, cls.baseurl2, cls.pattern2, matchdict

    def post_search_hook(self, i, matchdict):

        # extracting start times and end times
        start = datetime(i['year'], i['month'], i['day'], i['hour'], i['minute'], i['second'])
        end = datetime(i['year'], i['month'], i['day'], i['ehour'], i['eminute'], i['esecond'])
        timerange = TimeRange(start, end)

        map_ = OrderedDict()
        map_['Time'] = timerange
        map_['Start Time'] = start.strftime(TIME_FORMAT)
        map_['End Time'] = end.strftime(TIME_FORMAT)
        map_['Instrument'] = matchdict['Instrument'][0]
        map_['Phsyobs'] = matchdict['Physobs'][0]
        map_['Source'] = matchdict['Source'][0]
        map_['Provider'] = matchdict['Provider'][0]
        map_['SatelliteNumber'] = i['SatelliteNumber']
        map_['Level'] = i['Level']
        map_['Wavelength'] = i['Wavelength']*u.Angstrom
        return map_

    def search(self, *args, **kwargs):
        supported_waves = [94, 131, 171, 195, 284, 304]*u.Angstrom
        all_waves = []
        baseurl1b, pattern1b, baseurl2, pattern2, matchdict = self.pre_search_hook(*args, **kwargs)
        req_wave = matchdict.get('Wavelength', None)
        if req_wave is not None:
            wmin = req_wave.min.to(u.Angstrom, equivalencies=u.spectral())
            wmax = req_wave.max.to(u.Angstrom, equivalencies=u.spectral())
            req_wave = a.Wavelength(wmin, wmax)
            for wave in supported_waves:
                if wave in req_wave:
                    all_waves.append(int(wave.value))
        else:
            all_waves = [int(i.value) for i in supported_waves]
        all_satnos = matchdict.get('SatelliteNumber')
        all_levels = matchdict.get('Level')
        metalist = []

        # iterating over all possible Attr values through loops
        for satno in all_satnos:
            for level in all_levels:
                for wave in all_waves:
                    formdict = {'wave': wave, 'SatelliteNumber': satno}
                    if str(level) == '1b':
                        formdict['elem'] = 'fe'
                        if wave == 304:
                            formdict['elem'] = 'he'
                        baseurl = baseurl1b
                        pattern = pattern1b
                    elif str(level) == '2':
                        baseurl = baseurl2
                        pattern = pattern2
                    else:
                        raise ValueError(f"Level {level} is not supported.")
                    # formatting baseurl using Level, SatelliteNumber and Wavelength
                    urlpattern = baseurl.format(**formdict)

                    scraper = Scraper(urlpattern)
                    filesmeta = scraper._extract_files_meta(matchdict['Time'], extractor=pattern)
                    for i in filesmeta:
                        map_ = self.post_search_hook(i, matchdict)
                        metalist.append(map_)

        return QueryResponse(metalist, client=self)

    @classmethod
    def _attrs_module(cls):
        return 'goes', 'sunpy.net.dataretriever.attrs.goes'

    @classmethod
    def register_values(cls):
        from sunpy.net import attrs
        goes_number = [16, 17]
        adict = {attrs.Instrument: [
            ("SUVI", "GOES Solar Ultraviolet Imager.")],
            attrs.goes.SatelliteNumber: [(str(x), f"GOES Satellite Number {x}") for x in goes_number],
            attrs.Source: [('GOES', 'The Geostationary Operational Environmental Satellite Program.')],
            attrs.Physobs: [('flux', 'a measure of the amount of radiation received by an object from a given source.')],
            attrs.Provider: [('NOAA', 'The National Oceanic and Atmospheric Administration.')],
            attrs.Level: [('1b', 'Solar images at six wavelengths with image exposures 10 msec or 1 sec.'),
                          ('2', 'Weighted average of level-1b product files of SUVI.')]}
        return adict
