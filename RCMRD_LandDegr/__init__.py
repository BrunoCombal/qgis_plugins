# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RCMRD_LandDegr
                                 A QGIS plugin
 Compute dand degradation indices
                             -------------------
        begin                : 2015-10-16
        copyright            : (C) 2015 by Bruno Combal, MESA
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
    """Load RCMRD_LandDegr class from file RCMRD_LandDegr.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .land_degr import RCMRD_LandDegr
    return RCMRD_LandDegr(iface)
