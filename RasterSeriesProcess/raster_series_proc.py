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
        self.forcedNoData = -32768
        self.noDataIsSet = True

        
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

    # ______________________________________
    def logMsg(self, msg, errorLvl=QgsMessageLog.INFO):
        QgsMessageLog.logMessage(msg, tag='Raster Processing',level=errorLvl)
    #_______________________________________
    def deleteEntry(self):
        # files are identified by name: it is possible to have 2 (or more) files having the same name.
        thisPosition = []
        for item in self.dlg.widgetListFiles.selectedItems():
            # remove from widget
            self.dlg.widgetListFiles.takeItem(self.dlg.widgetListFiles.row(item))
            # remove from raster_list
            for ii in range( len(self.raster_list) ):
                if self.raster_list[ii].name() == item.text():
                    del self.raster_list[ ii ]
                    break

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
        listFID = []
        if self.outfile['max'] is None:
            self.iface.messageBar().pushMessage("Info","You must define an output file")
            return False


        # open all files in self.raster_list
        for ii in self.raster_list:
            fid = gdal.Open(ii.source(), GA_ReadOnly)
            if not fid:
                self.logMsg("Could not open file "+ii.source()+". Abort processing")
                return False
            else:
                self.logMsg("Opening file "+str(ii.source()))
            listFID.append(fid)

        # output has the definition of the first file
        ns = listFID[0].RasterXSize
        nl = listFID[0].RasterYSize
        nb = listFID[0].RasterCount
        if not self.noDataIsSet:
            noDataValue = listFID[0].GetRasterBand(1).GetNoDataValue()
            self.logMsg("No data set to "+str(noDataValue))
        else:
            noDataValue = self.forcedNoData
            self.logMsg("self.noDataIsSet; no data set to "+str(noDataValue))
        projection = listFID[0].GetProjection()
        geoTrans = listFID[0].GetGeoTransform()
        self.logMsg("Output image: ns={0}, nl={1}".format(ns, nl))
        
        # init output file
        format='GTiff'
        options=['compress=LZW']
        outType='Float32'
        outDrv = gdal.GetDriverByName(format)
        outDs = outDrv.Create(self.outfile['max'], ns, nl, nb, self.ParseType(outType), options)
        outDs.SetProjection(projection)
        outDs.SetGeoTransform(geoTrans)
        avgArr = []

        # let's scan the image line by line (save memory)
        for il in range(nl):
            data=[]
            for ifile in listFID: # get data from all files
                thisDataset = numpy.ravel(ifile.GetRasterBand(1).ReadAsArray(0, il, ns, 1).astype(float))
                data.append(thisDataset)

            data = numpy.asarray(data)
            # let's sum all files' data, per pixel
            if noDataValue is not None: # conditional sum
                sum = (data * (data != noDataValue)).sum(axis=0)
                #QgsMessageLog.logMessage("max sum "+str(sum.max()))
                count = (data != noDataValue).sum(axis=0)
                #QgsMessageLog.logMessage(str( len(count) ))
                avg = numpy.zeros(ns)*noDataValue
                wdiv = count != 0
                if wdiv.any(): # where division is allowed, else skip to the next line
                    #QgsMessageLog.logMessage("size "+str(wdiv.size))
                    avg[wdiv] = sum[wdiv] / count[wdiv].astype(float)

            else: # sum everything
                sum = data.sum(axis=0)
                avg = sum / len(listFID).astype(float)
                
            # now put the current line back in the memory arrays
            avgArr.append(avg)
        
        # compute average
        #QgsMessageLog.logMessage("Writing output")
        outDs.GetRasterBand(1).WriteArray(numpy.asarray(avgArr), 0, 0)

        # close files
        for ii in listFID:
            ii = None
        
        return True
            
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
            # if asked, open result in canvas
            self.iface.addRasterLayer( self.outfile['max'], QFileInfo(self.outfile['max']).baseName() )
            
