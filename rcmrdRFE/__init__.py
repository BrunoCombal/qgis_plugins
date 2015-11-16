# -*- coding: utf-8 -*-
"""
/***************************************************************************
 rcmrdRFE
                                 A QGIS plugin
 Compute RCMRD indicator of rainfall erosivity
                             -------------------
        begin                : 2015-11-16
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
    """Load rcmrdRFE class from file rcmrdRFE.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .rcmrd_rfe import rcmrdRFE
    return rcmrdRFE(iface)
