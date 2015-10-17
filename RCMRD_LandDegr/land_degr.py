# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RCMRD_LandDegr
                                 A QGIS plugin
 Compute dand degradation indices
                              -------------------
        begin                : 2015-10-16
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Bruno Combal, MESA
        email                : bruno.combal@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from land_degr_dialog import RCMRD_LandDegrDialog
import os.path


class RCMRD_LandDegr:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'RCMRD_LandDegr_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = RCMRD_LandDegrDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Land Degradation (RCMRD)')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'RCMRD_LandDegr')
        self.toolbar.setObjectName(u'RCMRD_LandDegr')

        # Declare user instance variables
        self.roiDefinitions = None
        self.roiDefinitions = [{"name":"IGAD", "roiXY":[21.8094, -4.6775, 51.417, 22.227]},
            {"name":"Djibouti", "roiXY":[41.749110148,10.929824931, 43.418711785,12.707912502]},
            {"name":"Eritrea", "roiXY":[36.423647095,12.360021871, 43.123871290,18.004828192]},
            {"name":"Ethiopia", "roiXY":[32.989799845,3.403333435, 47.979169149,14.879532166]},
            {"name":"Kenya", "roiXY":[33.890468384,-4.677504165, 41.885019165,5.030375823]},
            {"name":"Sudan", "roiXY":[42.647246541,7.996515605, 48.93911199991,11.498928127]},
            {"name":"South Sudan", "roiXY":[24.121555623,3.490201518, 35.920835409,12.216154684]},
            {"name":"Somali Land", "roiXY":[42.647246541,7.996515605, 48.93911199991,11.498928127]},
            {"name":"Somalia", "roiXY":[40.965385376,-1.69628316498, 51.417037811,11.989118646]},
            {"name":"Uganda", "roiXY":[29.548459513,-1.475205994, 35.006472615,4.219691875]}]
        self.selectedRoi = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('RCMRD_LandDegr', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/RCMRD_LandDegr/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Land Degradation Indices'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Land Degradation (RCMRD)'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def doCheckToGo(self):
        if (self.selectedRoi) is None:
            return False
        return True

    def displayRoiValues(self):
        if self.dlg.comboChooseArea.currentIndex() is not None:
            listRoiNames = []
            listRoiNames = [ ii["name"] for ii in self.roiDefinitions ]
            self.selectedRoi = listRoiNames[self.dlg.comboChooseArea.currentIndex()]
            # West, xmin, roiXY[0]
            self.dlg.RoiWestEdit.setText( "%12.7f" % [ f["roiXY"][0] for f in self.roiDefinitions if (f["name"]==self.selectedRoi) ][0]  )
            self.dlg.RoiWestEdit.displayText
            # East, xmax, roiXY[2]
            self.dlg.RoiEastEdit.setText( "%12.7f" % [ f["roiXY"][2] for f in self.roiDefinitions if (f["name"]==self.selectedRoi) ][0]  )
            self.dlg.RoiEastEdit.displayText
            # South, ymin, roiXY[1]
            self.dlg.RoiSouthEdit.setText( "%12.7f" % [ f["roiXY"][1] for f in self.roiDefinitions if (f["name"]==self.selectedRoi) ][0]  )
            self.dlg.RoiEastEdit.displayText
            # North ymax, roiXY[3]
            self.dlg.RoiNorthEdit.setText( "%12.7f" % [ f["roiXY"][3] for f in self.roiDefinitions if (f["name"]==self.selectedRoi) ][0]  )
            self.dlg.RoiEastEdit.displayText

        return

    def run(self):
        """Set up the interface content and call business-logic functions"""

        # clear all widgets first
        self.dlg.comboChooseArea.clear()
        self.dlg.comboVegetationIndex.clear()
        self.dlg.comboPopDensity.clear()
        self.dlg.comboRainfallErosivity.clear()
        self.dlg.comboSlopeLF.clear()
        self.dlg.comboSoilErodibility.clear()
        self.dlg.logTextDump.clear()

        self.dlg.logTextDump.append("Initialising...")
        # setup "settings" tools. ROI are defined with xMin, yMin, xMax, yMax
        self.dlg.comboChooseArea.addItems( [ ii["name"] for ii in self.roiDefinitions ] )
        for ii in self.roiDefinitions:
            self.dlg.logTextDump.append( ii["name"] )
        self.dlg.comboChooseArea.currentIndexChanged.connect(self.displayRoiValues)

        # setup input files
        self.dlg.logTextDump.append("Scanning loaded files")
        layers = self.iface.legendInterface().layers()
        vector_list = []
        raster_list = []
        # detect vectors and rasters already loaded in QGis
        for layer in layers:
            layerType = layer.type()
            
            if (layerType == QgsMapLayer.VectorLayer) and (layer.wkbType()==QGis.WKBPolygon):
                vector_list.append(layer.name())
                QgsMessageLog.logMessage("--- Vector")
                #QgsMessageLog.logMessage(str(dir(layer)))
                print layer.geometryType()
                QgsMessageLog.logMessage('Vector: '+str(layer.name())+ ' '+str(layer.geometryType()))
            if layerType == QgsMapLayer.RasterLayer:
                raster_list.append(layer.name())

        # Assign the pre-loaded rasters and vectors to the interface objects
        self.dlg.comboVegetationIndex.addItems(raster_list)
        self.dlg.comboPopDensity.addItems(raster_list)
        self.dlg.comboRainfallErosivity.addItems(raster_list)
        self.dlg.comboSlopeLF.addItems(raster_list)
        self.dlg.comboSoilErodibility.addItems(raster_list)
        
        # show the dialog
        self.dlg.show()
        self.dlg.logTextDump.append("Waiting for settings")
        # Run the dialog event loop, and exit only if all check are ok
        checkToGo = False
        while not checkToGo:
            result = self.dlg.exec_()
            if result:
                checkToGo = self.doCheckToGo()
            else:
                checkToGo = True
        self.dlg.logTextDump.append("Application running.")
        #self.iface.messageBar().pushMessage("Info","Running")

        # See if OK was pressed
        if result:
            # check that all required parameters are set, else trigger an error message
            self.iface.messageBar().pushMessage("Info","result is true")
            QgsMessageLog.logMessage("Value is " + str(self.dlg.data1.value()))
