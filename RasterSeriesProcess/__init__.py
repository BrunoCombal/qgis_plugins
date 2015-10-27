# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RasterSeriesProcess
                                 A QGIS plugin
 Perform various processing on series of rasters
                             -------------------
        begin                : 2015-10-26
        copyright            : (C) 2015 by Bruno Combal
        email                : bruno.combal@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load RasterSeriesProcess class from file RasterSeriesProcess.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .raster_series_proc import RasterSeriesProcess
    return RasterSeriesProcess(iface)
