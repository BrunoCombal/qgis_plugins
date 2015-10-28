# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RasterSeriesProcess
                                 A QGIS plugin
 Perform various processing on series of rasters
                              -------------------
        begin                : 2015-10-26
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Bruno Combal
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFile, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.core import *
# gdal
from osgeo import gdal
from osgeo.gdalconst import *
import numpy
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from raster_series_proc_dialog import RasterSeriesProcessDialog
import os.path

class RasterSeriesProcess:
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
            'RasterSeriesProcess_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = RasterSeriesProcessDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Raster Series Processing')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'RasterSeriesProcess')
        self.toolbar.setObjectName(u'RasterSeriesProcess')


        # self objected
        self.raster_list=[]
        self.outfile = {"max":None, "min":None, "avg":None, "median":None}

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
        return QCoreApplication.translate('RasterSeriesProcess', message)


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
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    #_______________________________________
    def deleteEntry(self):
        self.iface.messageBar().pushMessage("Info","Deleting!")
        for item in self.dlg.widgetListFiles.selectedItems():
            self.dlg.widgetListFiles.takeItem(self.dlg.widgetListFiles.row(item))
            # must also remove entry in raster_list
            self.iface.messageBar().pushMessage('Info',"Missing implementation of raster_list clear up")
            #QgsMessageLog.logMessage("Missing implementation of raster_list clean up")

    #________________________________________
    # let the user define a path and filename
    def defineFile(self):
        outfile = QFileDialog.getSaveFileName(self.dlg, "Define an output filename",
                                                    os.path.expanduser("~"))
        if outfile:
            self.dlg.lineEdit_maxOut.setText(outfile)
            self.outfile["max"]=outfile

    def ParseType(self, type):
        if type == 'Byte':
	        return GDT_Byte
        elif type == 'Int16':
	        return GDT_Int16
        elif type == 'UInt16':
	        return GDT_UInt16
        elif type == 'Int32':
	        return GDT_Int32
        elif type == 'UInt32':
	        return GDT_UInt32
        elif type == 'Float32':
	        return GDT_Float32
        elif type == 'Float64':
	        return GDT_Float64
        elif type == 'CInt16':
	        return GDT_CInt16
        elif type == 'CInt32':
	        return GDT_CInt32
        elif type == 'CFloat32':
	        return GDT_CFloat32
        elif type == 'CFloat64':
	        return GDT_CFloat64
        else:
	    return GDT_Float32

    def doProcessing(self):
        self.iface.messageBar().pushMessage("outfile max:"+self.outfile['max'])
        if self.outfile['max'] is None:
            self.iface.messageBar().pushMessage("Info","You must define an output file")
            return False


        # list of files is in self.rasterList
        # in a loop: sum-up and detect the no-data, in preparation of the division

        # output has the definition of the first file
        fid0 = gdal.Open(self.raster_list[0].source(), GA_ReadOnly)
        ns = fid0.RasterXSize
        nl = fid0.RasterYSize
        nb = fid0.RasterCount
        noDataValue = fid0.GetRasterBand(1).GetNoDataValue()

        projection = fid0.GetProjection()
        geoTrans = fid0.GetGeoTransform()
        fid0 = None # equivalent to fid0.close()

        #QgsMessageLog.logMessage("ns: "+ str(ns) + " nl:" + str(nl) + " nb:" + str(nb))
        # init result with the first file, then loop over the rest
        format='GTiff'
        options=['compress=LZW']
        outType='Float32'
        outDrv = gdal.GetDriverByName(format)
        outDs = outDrv.Create(self.outfile['max'], ns, nl, nb, self.ParseType(outType), options)
        outDs.SetProjection(projection)
        outDs.SetGeoTransform(geoTrans)
        nCount = None
        sumArr = None

        for ii in self.raster_list:
            #basename = QFileInfo(ii).baseName()
            #pathname = QFileInfo(ii).path()
            # QgsMessageLog.logMessage("Path " + pathname + " file: "+basename )
            source = ii.source()
            # process line by line: avoid bloating memory, barely slower
            #QgsMessageLog.logMessage("--- Opening file: "+ii.source())
            fid = gdal.Open(ii.source(), GA_ReadOnly)
            if not fid:
                self.iface.messageBar().pushMessage("Info","Error opening file")
                #QgsMessageLog.logMessage("Error opening file")
            if sumArr is None:
                #QgsMessageLog.logMessage("Initializing...")
                sumArr = fid.GetRasterBand(1).ReadAsArray(0, 0, ns, nl).astype(float)
                if noDataValue is not None:
                    wnodata = sumArr != noDataValue
                    nCount  = numpy.zeros(ns * nl)
                    nCount[wnodata] = 1
                else:
                    nCount = numpy.ones(ns * nl)
            else:
                #QgsMessageLog.logMessage('adding up values')
                fullNoDataLine = 0
                for il in range(nl):
                    data = numpy.ravel(fid.GetRasterBand(1).ReadAsArray(0, il, ns, 1)).astype(float)
                    if noDataValue is not None:
                        wnodata = data != noDataValue
                        if wnodata.length():
                            sumArr[wnodata] = sumArr[wnodata] + data[wnodata]
                            nCount[wnodata] = nCount[wnodata] + 1
                        else:
                            fullNoDataLine += 1
                    else:
                        sumArr = sumArr + data
                        nCount = nCount + 1

                if (fulllNoDataLine == (nl-1)):
                    self.iface.messageBar().pushMessage('Info',"File "+ii.source()+": all pixels set to no data")
                    #QgsMessageLog.logMessage("File "+ii.source()+": all pixels set to no data")
            
            fid = None # release file, equivalent to fid.close()

        # compute average
        doWrite = False
        if noDataValue is not None:
            wnodata = sumArr != noDataValue
            if wnodata.length():
                sumArr[wnodata] = sumArr[wnodata] / nCount[wnodata].astype(float)
                doWrite = True
            else:
                self.iface.messageBar().pushMessage('Info','Average: all pixels set to no data')
                #QgsMessageLog.logMessage("Average: all pixels set to no data")
        else:
            sumArr = sumArr / nCount.astype(float)
            doWrite = True
        # write result
        if doWrite:
            #QgsMessageLog.logMessage("Writing output")
            outDs.GetRasterBand(1).WriteArry(sumArr.reshape(ns, nl), 0, 0)
        else:
            self.iface.messageBar().pushMessage('Could not write average file')
            #QgsMessageLog.logMessage("Could not write average file")


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/RasterSeriesProcess/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Raster Series Processings'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&Raster Series Processing'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        # reset widgets
        self.dlg.widgetListFiles.clear()
        # prepare connections
        self.dlg.buttonDelete.clicked.connect(self.deleteEntry)
        self.dlg.button_outMaxDir.clicked.connect(self.defineFile)

        self.layers = self.iface.legendInterface().layers()
        for layer in self.layers:
            layerType = layer.type()
            if layerType == QgsMapLayer.RasterLayer:
                self.raster_list.append(layer)
                self.dlg.widgetListFiles.addItem(layer.name())

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        checkToGo = False
        while not checkToGo: # if result returns false: exit
            result = self.dlg.exec_()
            if result:
                checkToGo = self.doProcessing()
            else:
                checkToGo = True
                
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            # force output file
            pass
