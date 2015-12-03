# -*- coding: utf-8 -*-
"""
/***************************************************************************
 rcmrdCombine
                                 A QGIS plugin
 Combine NDVI and LULC
                             -------------------
        begin                : 2015-12-03
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
    """Load rcmrdCombine class from file rcmrdCombine.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .rcmrd_combine import rcmrdCombine
    return rcmrdCombine(iface)
