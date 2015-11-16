# -*- coding: utf-8 -*-
"""
/***************************************************************************
 rcmrdRFE
                                 A QGIS plugin
 Compute RCMRD indicator of rainfall erosivity
                              -------------------
        begin                : 2015-11-16
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
import string
import numpy
# gdal
from osgeo import gdal
from osgeo.gdalconst import *
# Import the code for the dialog
from rcmrd_rfe_dialog import rcmrdRFEDialog
import os.path


class rcmrdRFE:
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
            'rcmrdRFE_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = rcmrdRFEDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&RCMRD Rainfall Erosivity')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'rcmrdRFE')
        self.toolbar.setObjectName(u'rcmrdRFE')

        # default values
        self.inDir='/Users/bruno/Desktop/mesa_data/input/Rainfall'
        self.dateStart={'day':1,'month':2,'year':2015}
        self.dateEnd={'day':1,'month':10,'year':2015}

        # filename convention
        self.fname={'prefix':'', 'suffix':'_rfe.tif'}

        # outfname
        self.outfile={'outDir':'/Users/bruno/Desktop/mesa_data/output/','rfe':'rfe.tif','rfd':'rfd.tif','rfi':'rfi.tif'}
        
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
        return QCoreApplication.translate('rcmrdRFE', message)


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

        icon_path = ':/plugins/rcmrdRFE/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'RCMRD RFE'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&RCMRD Rainfall Erosivity'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # ___________________
    def logMsg(self, msg, errorLvl=QgsMessageLog.INFO):
        QgsMessageLog.logMessage(msg, tag='Rainfall Erosivity',level=errorLvl)
        
    # ___________________
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

    # ___________________
    def YYYYMMDD_to_Num(self, yyyymmdd):
        # base set to 1900
        yyymmddStr = str(yyyymmdd)
        thisYear=int(yyyymmdd[0:4])
        thisMonth=int(yyyymmdd[4:6])
        thisDay=int(yyyymmdd[6:8])

        return (thisYear-1900)*36 + (thisMonth-1)*3 + (thisDay)/10 + 1
    # ___________________
    def Num_to_YYYYMMDD(self, count):
        # base set to 1900
        thisYear = count/36
        thisMonth = (count - (36 * thisYear))/3
        thisDay = (count - (36 * thisYear) - (3 * thisMonth))*10 + 1
        thisMonth += 1
        thisYear += 1900

        return '{}{:02}{:02}'.format(thisYear, thisMonth, thisDay)
    # ___________________
    def doCompute(self):
        # build list of filenames
        list_dates=[]
        list_files=[]
        numStart = self.YYYYMMDD_to_Num('{}{:02}{:02}'.format(self.dateStart['year'],self.dateStart['month'],self.dateStart['day']))
        numEnd = self.YYYYMMDD_to_Num( '{}{:02}{:02}'.format(self.dateEnd['year'], self.dateEnd['month'], self.dateEnd['day']) )

        for icount in range(numStart, numEnd + 1):
            thisDate = self.Num_to_YYYYMMDD(icount)
            self.logMsg('{} -> {}'.format(icount, thisDate))
            list_dates.append(thisDate)
            list_files.append( os.path.join(self.inDir, '{}{}{}'.format(self.fname['prefix'], thisDate,self.fname['suffix'])) )

        if len(list_files)==0:
            # error message
            exit
            
        test=True
        for ii in list_files:
            if not os.path.isfile(ii):
                test=False
                self.logMsg("Missing file: {}".format(ii) )
        # error message and exit
        if test==False:
            self.logMsg("Time series cannot be processed, missing files. Exit.")
            exit

        # let's open all files
        listFID=[]
        for ii in list_files:
            self.logMsg(ii)
            thisFID = gdal.Open(ii, GA_ReadOnly)
            listFID.append(thisFID)
        # let's instantiate the output
        thisProj = listFID[0].GetProjection()
        thisTrans = listFID[0].GetGeoTransform()
        ns = listFID[0].RasterXSize
        nl = listFID[0].RasterYSize
        format='GTiff'
        options=['compress=lzw']
        outType=GDT_Float32
        outDrv = gdal.GetDriverByName(format)
        self.logMsg( os.path.join(self.outfile['outDir'],self.outfile['rfe']))
        outDs = outDrv.Create(os.path.join(self.outfile['outDir'],self.outfile['rfe']),
                              ns, nl, 1, outType, options  )
        outDsRFD = outDrv.Create( os.path.join( self.outfile['outDir'], self.outfile['rfd']),
                                  ns, nl, 1, outType, options)
        outDsRFI = outDrv.Create( os.path.join( self.outfile['outDir'], self.outfile['rfi']),
                                  ns, nl, 1, outType, options)
        outDs.SetProjection(thisProj)
        outDs.SetGeoTransform(thisTrans)
        outDsRFD.SetProjection(thisProj)
        outDsRFD.SetGeoTransform(thisTrans)
        outDsRFI.SetProjection(thisProj)
        outDsRFI.SetGeoTransform(thisTrans)

        data=[]

        # parse by line
        for il in range(nl):
            data=[]
            # get the whole time series for this line
            for ifile in listFID:
                thisDataset = numpy.ravel(ifile.GetRasterBand(1).ReadAsArray(0, il, ns, 1).astype(float))
                data.append(thisDataset)
                
            data = numpy.asarray(data)
            sumDepth = data.sum(axis=0)

            # now we had values >= 40mm: let's put all data < 40mm to 0
            wLow = data < 40
            if wLow.any():
                data[wLow] = 0
            sumIntensity = data.sum(axis=0)
            
            sumErosivity = self.dlg.valueWRI.value()*sumIntensity + self.dlg.valueWRD.value()* sumDepth

            # write outputs
            self.logMsg('size {}'.format(sumErosivity.shape))
            self.logMsg('ns {}, nl {}'.format(ns, nl))
            outDs.GetRasterBand(1).WriteArray(sumErosivity.reshape(1,ns), 0, il)
            outDsRFI.GetRasterBand(1).WriteArray(sumIntensity.reshape(1,ns),0,il )
            outDsRFD.GetRasterBand(1).WriteArray(sumDepth.reshape(1,ns),0,il)

        # close files
        for ii in listFID:
            ii = None

        return True
    # ___________________
    def doInitGui(self):
        self.dlg.editInputDir.clear()
        self.dlg.editInputDir.setText( self.inDir )

    # ____________________
    def run(self):
        # initialise GUI
        self.doInitGui()
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            self.doCompute()

            
