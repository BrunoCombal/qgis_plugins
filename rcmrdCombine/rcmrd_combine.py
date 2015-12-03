# -*- coding: utf-8 -*-
"""
/***************************************************************************
 rcmrdCombine
                                 A QGIS plugin
 Combine NDVI and LULC
                              -------------------
        begin                : 2015-12-03
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFile, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from rcmrd_combine_dialog import rcmrdCombineDialog
import os.path
import string
import numpy, numpy.ma
import random
# gdal
from osgeo import gdal
from osgeo.gdalconst import *
import math
import processing

class rcmrdCombine:
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
            'rcmrdCombine_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = rcmrdCombineDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&RCMRD Combine')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'rcmrdCombine')
        self.toolbar.setObjectName(u'rcmrdCombine')
        
        self.clipLayer = None

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
        return QCoreApplication.translate('rcmrdCombine', message)


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

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/rcmrdCombine/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'RCMRD Combine'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&RCMRD Combine'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    # ___________________
    def logMsg(self, msg, errorLvl=QgsMessageLog.INFO):
        QgsMessageLog.logMessage(msg, tag='RCMD Combine',level=errorLvl)
        
        prepend=''
        if errorLvl==QgsMessageLog.WARNING:
            self.iface.messageBar().pushMessage("WARNING", msg)
            prepend="Warning! "
        if errorLvl==QgsMessageLog.CRITICAL:
            self.iface.messageBar().pushMessage("CRITICAL",msg)
            prepend="Critical error! "
        self.dlg.logTextDump.append(prepend + msg)
    # ________________
    def doInitGUI(self):
        # define temp directory
        self.dlg.editWrkDir.setText( os.path.join( os.path.expanduser("~"), "qgis_rcmrdplugin" ) )
        self.dlg.buttonWrkDir.clicked.connect(lambda: self.saveDir('WrkDir'))
        
        # connect open file buttons
        self.dlg.buttonNDVI.clicked.connect( (lambda: self.doOpenFile('ndvi')) )
        self.dlg.buttonLULC.clicked.connect( (lambda: self.doOpenFile('lulc')) )
        self.dlg.buttonclipShp.clicked.connect( (lambda: self.doOpenFile('clipShp')) )
        
        # connect button for saving
        self.dlg.buttonOut.clicked.connect( (lambda:self.saveFile('out')) )
        
        # open on help tab
        self.dlg.tabs.setCurrentWidget(self.dlg.tabHelp)

        
        return True
    # ___________________
    def doTmpName(self, fname):
        return '{}_{}.tif'.format(fname, random.randint(0,10000))
    # ________________
    def doCheckReady(self):
        # all files defined?
        if self.dlg.editNdvi.text()=='':
            self.logMsg("Please define an input NDVI file. Revise 'Inputs' tab.", QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        if self.dlg.editLULC.text()=='':
            self.logMsg("Please define an input LU/LC file. Revise 'Inputs' tab.", QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        if self.dlg.editClipShp.text()=='':
            self.logMsg("Please define an input clipping shapefile. Revise 'Inputs' tab.", QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
            
        if self.dlg.editOutFile.text()=='':
            self.logMsg("Please define an output file. Revise 'Outputs' tab.", QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        return True
    # ___________________
    def doOpenFile(self, selector):
        text = {'ndvi': 'NDVI file (5 Classes)','lulc':'LU/LC (5 Classes)','clipShp': 'clipping shapefile'}
        dialog = QFileDialog()
        fname = dialog.getOpenFileName(self.dlg, self.tr("Open {}".format(text[selector])) )
        if fname:
            if selector=='clipShp':
                # it must be a shapefile, let's open it
                self.clipLayer = QgsVectorLayer( fname, "Clip", 'ogr')
                if not self.clipLayer.isValid():
                    self.logMsg( "Could not load vector layer {} with {}".format(self.clipLayer.name(), fname), QgsMessageLog.WARNING)
                    self.dlg.logTextDump.append( "Could not load vector layer {}".format(self.clipLayer) )
                else:
                    self.dlg.editClipShp.setText(fname)
            if selector=='ndvi':
                self.dlg.editNdvi.setText(fname)
            if selector=='lulc':
                self.dlg.editLULC.setText(fname)
    # ____________________
    def saveFile(self, selector):
        text={'out':'Classified combination'}
        dialog = QFileDialog()
        fname = dialog.getSaveFileName(self.dlg, self.tr("Define a file name to save {}".format(text[selector])), os.path.expanduser("~"))
    
        if fname:
            # be sure to append '.tif'
            pathname, extension = os.path.splitext(fname)
            if extension!='.tif':
                fname = pathname + '.tif'
                
            if selector=='out':
                self.dlg.editOutFile.setText(fname)
                
        return True
    #____________________
    def saveDir(self, selector):
        text={'WrkDir':'intermediate processing'}
        dialog = QFileDialog()
        dname = dialog.getExistingDirectory(self.dlg, self.tr("Choose a directory to save {}".format(text[selector])), os.path.expanduser("~"))
        if dname:
            if selector=='WrkDir':
                self.dlg.editWrkDir.setText(dname)
    # ________________
    def doGetClasses(self):
        classes = []
        classes.append([self.dlg.spinMin1.value(), self.dlg.spinMax1.value()])
        classes.append([self.dlg.spinMin2.value(), self.dlg.spinMax2.value()])
        classes.append([self.dlg.spinMin3.value(), self.dlg.spinMax3.value()])
        classes.append([self.dlg.spinMin4.value(), self.dlg.spinMax4.value()])
        classes.append([self.dlg.spinMin5.value(), self.dlg.spinMax5.value()])
        
        return classes
    # ________________
    def getCRS(self, file):
        thisFid = gdal.Open(file, GA_ReadOnly)
        thisCRS = thisFid.GetProjection()
        thisTrans = thisFid.GetGeoTransform()
        
        return thisCRS, thisTrans
    # ________________
    def doReproj(self, infile, outfile, proj, geoTrans):
        # clipping layer
        if self.clipLayer is not None:
            ext = self.clipLayer.extent()
            bb  = [ ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum() ]
            extraParam = '-dstnodata 0 -te {} {} {} {} -cutline "{}" -crop_to_cutline '.format(bb[0], bb[1], bb[2], bb[3], self.dlg.editClipShp.text() )
    
        thisCRS, thisGT = self.getCRS(infile)
    
        self.logMsg('{}: projection is {}'.format(infile, thisCRS))
        self.logMsg('Projection file is {}'.format(outfile))
        testproc = processing.runalg('gdalogr:warpreproject',
            infile, # input
            thisCRS, # source ss
            proj, # dest srs
            '', # no data, <parameterString>
            math.fabs(geoTrans[1]), # target resolution: 0=unchanged
            0, # method: thematic layers, use 0
            0, # output raster type
            2, # compression
            None, # jpeg compression
            None, # zlevel
            None, # predictor
            None, # tiled
            None, # bigtiff
            None, # TFW
            extraParam, # extra 
            outfile)
    
        return True
    # ________________
    def doProcessing(self):
        ndviFile = self.dlg.editNdvi.text()
        lulcFile = self.dlg.editLULC.text()
        classes = self.doGetClasses()
        self.clipLayer = QgsVectorLayer( self.dlg.editClipShp.text(), "Clip", 'ogr')
        
        
        for ii in classes:
            self.logMsg( 'From {} to {}'.format(ii[0], ii[1]) )
        # reproject to LULC resolution
        proj, geoTrans = self.getCRS(lulcFile)
        
        tmpdir = self.dlg.editWrkDir.text()
        ndviFileReproj = os.path.join( tmpdir, self.doTmpName( os.path.basename(ndviFile)) )
        self.doReproj(ndviFile, ndviFileReproj, proj, geoTrans)
        
        lulcFileReproj = os.path.join(tmpdir, self.doTmpName( os.path.basename(lulcFile)) )
        self.doReproj(lulcFile, lulcFileReproj , proj, geoTrans)
        
        outProj, outGeoTrans = self.getCRS(ndviFileReproj)
        
        # math and classification in 1 go
        thisNDVI = gdal.Open(ndviFileReproj, GA_ReadOnly)
        thisLULC = gdal.Open(lulcFileReproj, GA_ReadOnly)
        ns = thisNDVI.RasterXSize
        nl = thisNDVI.RasterYSize
        projection = thisNDVI.GetProjection()
        geotrans = thisLULC.GetGeoTransform()
        outDrv = gdal.GetDriverByName('GTiff')
        outFID = outDrv.Create( self.dlg.editOutFile.text(), ns, nl, 1, GDT_Byte )
        outFID.SetProjection(outProj)
        outFID.SetGeoTransform(outGeoTrans)
        
        for il in range(nl):
            dataNDVI = numpy.ravel( thisNDVI.GetRasterBand(1).ReadAsArray(0,il, ns, 1) )
            dataLULC = numpy.ravel( thisLULC.GetRasterBand(1).ReadAsArray(0,il, ns, 1) )
            wtc = (dataNDVI > 0) * (dataNDVI <=5) * (dataLULC > 0) * (dataLULC <=5)
            data = numpy.zeros(ns)
            if wtc.any():
                data[wtc] = dataNDVI[wtc] + dataLULC[wtc]
                recode = data.copy()
                for iclass,ii in zip(classes, range(1,len(classes)+1)):
                    wtr = (data > iclass[0] ) * (data<= iclass[1])
                    if wtr.any():
                        recode[wtr] = ii
                data = recode.copy()
                
            outFID.GetRasterBand(1).WriteArray( data.reshape(1,ns), 0, il)

        return True
    # ________________
    def run(self):
        """Run method that performs all the real work"""
        self.doInitGUI()
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        okToGo = False
        while not okToGo:
            result = self.dlg.exec_()
            if result:
                okToGo = self.doCheckReady()
            else:
                okToGo = True
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            jobOK = self.doProcessing()
            if jobOK:
                self.iface.addRasterLayer(unicode(self.dlg.editOutFile.text()), 'NDVI + LULC')