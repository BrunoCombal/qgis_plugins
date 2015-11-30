# -*- coding: utf-8 -*-
"""
/***************************************************************************
 rcmrdNatBreaks
                                 A QGIS plugin
 Classify a raser with Natural Breaks
                              -------------------
        begin                : 2015-11-24
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
from rcmrd_natBreak_dialog import rcmrdNatBreaksDialog
import os.path
# gdal
from osgeo import gdal
from osgeo.gdalconst import *
import numpy
import string
import os, os.path
# for computing natural_breaks distribution
from pysal.esda.mapclassify import Natural_Breaks

class rcmrdNatBreaks:
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
            'rcmrdNatBreaks_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = rcmrdNatBreaksDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&RCMRD Natural Breaks')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'rcmrdNatBreaks')
        self.toolbar.setObjectName(u'rcmrdNatBreaks')

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
        return QCoreApplication.translate('rcmrdNatBreaks', message)


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

        icon_path = ':/plugins/rcmrdNatBreaks/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'RCMRD: Natural Breaks'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&RCMRD Natural Breaks'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
       
    # ____________
    def logMsg(self, msg, errorLvl = QgsMessageLog.INFO):
        QgsMessageLog.logMessage( msg, tag='Natural Breaks', level=errorLvl)
        
        prepend=''
        if errorLvl==QgsMessageLog.WARNING:
            self.iface.messageBar().pushMessage("WARNING", msg)
            prepend="Warning! "
        if errorLvl==QgsMessageLog.CRITICAL:
            self.iface.messageBar().pushMessage("CRITICAL",msg)
            prepend="Critical error! "
        self.dlg.logTextDump.append(prepend + msg)
    # ____________
    def doOpenFile(self):
        dialog = QFileDialog()
        fname = QFileDialog.getOpenFileName(self.dlg, self.tr("Open input file") )
        if fname:
            self.dlg.editInFile.setText(fname)
    # ____________
    def doSaveFile(self):
        dialog = QFileDialog()
        saveFname = QFileDialog.getSaveFileName(self.dlg, self.tr("Define an output file name for classification"), os.path.expanduser("~"))
        if saveFname:
            self.dlg.editOutFile.setText(saveFname)
    # ____________
    def doCheckToGo(self):
        if self.dlg.editInFile.text()=='':
            self.logMsg("Missing an input file", QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget( self.dlg.tabMessages )
            return False
        if self.dlg.editOutFile.text()=='':
            self.logMsg("Missing an output file", QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget( self.dlg.tabMessages )
            return False
        return True
    # ____________
    def doInitGUI(self):
        # connect buttons
        self.dlg.buttonInFile.clicked.connect( self.doOpenFile )
        self.dlg.buttonOutFile.clicked.connect( self.doSaveFile )
        # select input file tab
        self.dlg.tabs.setCurrentWidget( self.dlg.tabFiles)
    # ____________
    def getSampling(self):
        sampling = 12
        if self.dlg.radioAll.isChecked():
            sampling = 1
        if self.dlg.radio4th.isChecked():
            sampling = 4
        if self.dlg.radio6th.isChecked():
            sampling = 6
        if self.dlg.radio8th.isChecked():
            sampling = 8
        if self.dlg.radio10th.isChecked():
            sampling = 10
        if self.dlg.radio12th.isChecked():
            sampling = 12
        if self.dlg.radio16th.isChecked():
            sampling = 16
        if self.dlg.radio20th.isChecked():
            sampling = 20

        self.logMsg("Sampling is 1/{} pixels".format(sampling), QgsMessageLog.INFO)
        return sampling
    # ____________
    def doNatBreaks(self):
        # read the image: 1/NSkip lines, 1/NSkip column
        fname = self.dlg.editInFile.text()
        fid = gdal.Open(fname, GA_ReadOnly)
        if fid is None:
            self.logMsg("Could not open file {}".format(fname), QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget( self.dlg.tabMessages )
            return False
        ns = fid.RasterXSize
        nl = fid.RasterYSize
        projection = fid.GetProjection()
        trans = fid.GetGeoTransform()
        noData=fid.GetRasterBand(1).GetNoDataValue()
        self.logMsg("No data set to {}".format(noData))
        data = []
        NSkip = self.getSampling()
        
        self.logMsg("Classification: reading input")
        for il in range(0, nl, NSkip):
            thisData = numpy.ravel( fid.GetRasterBand(1).ReadAsArray(0, il, ns, 1) )
            data.append(thisData[range(0, ns, NSkip)])
        
        # compute natural breaks: the object must be unidimensional, and have a copy function
        # is there any no data?
        tmpData = numpy.ravel(data)
        if noData is not None:
            wdata = (tmpData != noData)
            if wdata.any():
                data = tmpData[wdata]
                del tmpData
        else:
            data = tmpData
            del tmpData
        self.logMsg("Classification: searching for natural_breaks")
        nBreaks = self.dlg.spinClasses.value()
        natBreaks = Natural_Breaks(numpy.ravel(data), k= nBreaks)
        bins=[0]
        bins.extend(natBreaks.bins)
        len_bins = len(bins)
        data = None
        natBreaks = None
        # write out results
        self.logMsg( "Natural breaks for {}".format(fname) )
        self.logMsg( "Classification: recoding" )
        for ii in range(1,len_bins):
            self.logMsg("Class {}: {}".format(ii, bins[ii]))
        # instead of duplicating the image in memory, let's do now the work line by line: memory friendly
        outName = self.dlg.editOutFile.text()
        outDrv = gdal.GetDriverByName('GTiff')
        outDs = outDrv.Create(outName, ns, nl, 1, GDT_Byte, ['compress=LZW'])
        outDs.SetProjection( projection )
        outDs.SetGeoTransform( trans )
        self.logMsg("Classification: saving data")
        for il in range(nl):
            data = numpy.ravel(fid.GetRasterBand(1).ReadAsArray(0, il, ns, 1))
            recoded = numpy.zeros(ns)
            icode=0
            for iclass in range(1,len_bins):
                icode+=1
                wtr = (data > bins[iclass-1])*(data <= bins[iclass])
                if wtr.any():
                    recoded[wtr]=icode
            outDs.GetRasterBand(1).WriteArray(recoded.reshape(1,ns), 0, il)

        return True
    # ____________
    def run(self):
        
        self.doInitGUI()
        self.dlg.show()
        # Run the dialog event loop
        jobDone = False
        result = False
        while not jobDone:
            result = self.dlg.exec_()
            if result:
                if self.doCheckToGo():
                    jobDone = self.doNatBreaks()
            else:
                jobDone = True
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            self.iface.addRasterLayer( self.dlg.editOutFile.text() , 'Result (Natural Breaks)')
