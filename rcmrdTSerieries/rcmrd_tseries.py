# -*- coding: utf-8 -*-
"""
/***************************************************************************
 rcmrdTSerieries
                                 A QGIS plugin
 Process rasters time series
                              -------------------
        begin                : 2015-11-17
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
from rcmrd_tseries_dialog import rcmrdTSerieriesDialog
import os, os.path
import datetime
import random
import processing

class rcmrdTSerieries:
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
            'rcmrdTSerieries_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = rcmrdTSerieriesDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&RCMRD Time Series')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'rcmrdTSerieries')
        self.toolbar.setObjectName(u'rcmrdTSerieries')
        self.clipLayer = None # the layer loaded in memory

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
        return QCoreApplication.translate('rcmrdTSerieries', message)


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

        icon_path = ':/plugins/rcmrdTSerieries/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'RCMRD Time Series'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&RCMRD Time Series'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # ___________________
    def logMsg(self, msg, errorLvl=QgsMessageLog.INFO):
        QgsMessageLog.logMessage(msg, tag='Rainfall Erosivity',level=errorLvl)
        
        prepend=''
        if errorLvl==QgsMessageLog.WARNING:
            self.iface.messageBar().pushMessage("WARNING", msg)
            prepend="Warning! "
        if errorLvl==QgsMessageLog.CRITICAL:
            self.iface.messageBar().pushMessage("CRITICAL",msg)
            prepend="Critical error! "
        self.dlg.logTextDump.append(prepend + msg)
        
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
        Yyymmddstr = str(yyyymmdd)
        thisYear=int(yyyymmdd[0:4])
        thisMonth=int(yyyymmdd[4:6])
        thisDay=int(yyyymmdd[6:8])

        return (thisYear-1900)*36 + (thisMonth-1)*3 + (thisDay)/10 
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
    def doOpenDir(self, dirSelector):
        dirName = QFileDialog.getExistingDirectory(self.dlg, self.tr('Choose directory'), os.path.expanduser("~"))
        if dirName:
            if dirSelector=='inDir':
                self.dlg.editInDir.setText(dirName)
    # ___________________
    def doOpenFile(self, selector):
        text = {'clipShp': 'clipping shapefile'}
        fname = QFileDialog.getOpenFileName(self.dlg, self.tr("Open {}".format(text[selector])) )
        if fname:
            if selector=='clipShp':
                # it must be a shapefile, let's open it
                self.clipLayer = QgsVectorLayer( fname, "Clip", 'ogr')
                if not self.clipLayer.isValid():
                    self.logMsg( "Could not load vector layer {} with {}".format(self.clipLayer.name(), fname), QgsMessageLog.WARNING)
                    self.dlg.logTextDump.append( "Could not load vector layer {}".format(self.clipLayer) )
                else:
                    self.dlg.editClipShp.setText(fname)
    # ___________________
    def doSaveFname(self, selector):
    
        text={'average':'Average', 'min':'Minimum', 'max':'Maximum'}
        saveFname = QFileDialog.getSaveFileName(self.dlg, self.tr("Define a file name to save {}".format(text[selector])), os.path.expanduser("~"))
        if saveFname:
            if selector=='average':
                self.dlg.editOutAverage.setText(saveFname)
            if selector=='minimum':
                self.dlg.editOutMinimum.setText(saveFname)
            if selector=='maximum':
                self.dlg.editOutMaximum.setText(saveFname)
    # ___________________
    def doClipShpWidgetsUpdate(self):
        if self.dlg.checkClipShp.isChecked():
            self.dlg.editClipShp.setEnabled(True)
            self.dlg.buttonClipShp.setEnabled(True)
        else:
            self.dlg.editClipShp.setEnabled(False)
            self.dlg.buttonClipShp.setEnabled(False)
    # ___________________
    def doInitGui(self):
        #self.dlg.editInDir.clear()
        if self.dlg.editInDir.text()=='':
            self.dlg.editInDir.setText( os.path.expanduser("~") )
        self.dlg.buttonInDir.clicked.connect( (lambda: self.doOpenDir('inDir')) )
        
        self.dlg.editPrefix.clear()
        self.dlg.editPrefix.setText('')
        
        self.dlg.editSuffix.clear()
        self.dlg.editSuffix.setText('_NDV.tif')
        
        self.dlg.editOutAverage.clear()
        self.dlg.buttonOutAverage.clicked.connect((lambda: self.doSaveFname('average')))
        
        # signals for clipShp widgets
        self.dlg.checkClipShp.stateChanged.connect( self.doClipShpWidgetsUpdate )
        self.dlg.buttonClipShp.clicked.connect( (lambda: self.doOpenFile('clipShp') ) )
    # ____________________
    # return False if any test is not past
    def doCheckReady(self):
    
        # do we have something to do?
        toDo=False
        if self.dlg.checkAverage.checkState():
            toDo=True
        if self.dlg.checkMinimum.checkState():
            toDo=True
        if self.dlg.checkMaximum.checkState():
            toDo=True
        if toDo==False:
            self.logMsg("Nothing to do! Please choose something to compute under tab 'Output file'")
            self.iface.messageBar().pushMessage("Info","Please choose a processing under tab 'Output file'", level=QgsMessageBar.WARNING)
            return False
    
        # Check input directory
        inDir=self.dlg.editInDir.text()
        if not os.path.isdir(inDir):
            self.logMsg('{} is not a directoy. Please correct input directory, in "Input files" tab.'.format(inDir), QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
             
        # Check input files
        list_files = self.doCreateFNameList()
        if list_files == False:
            self.logMsg('Missing files. Please check input directory, prefix, suffix and dates in the "Input files" tab.', QgsMessageLog.CRITICAL)
             
        # check ouput file(s)
        if self.dlg.checkAverage.checkState():
            if self.dlg.editOutAverage.text() == '':
                self.logMsg('Please define an output file name for Average, in "Output files" tab.', QgsMessageLog.CRITICAL)
                self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
                return False
                
        if self.dlg.checkMinimum.checkState():
            if self.dlg.editOutMinimum.text() == '':
                self.logMsg('Please define an output file name for Minimum, in "Output files" tab.', QgsMessageLog.CRITICAL)
                self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
                return False
                
        if self.dlg.checkMaximum.checkState():
            if self.dlg.editOutMaximum.text() == '':
                self.logMsg('Please define an output file name for Maximum, in "Output files" tab.', QgsMessageLog.CRITICAL)
                self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
                return False
            
        return True
    # ___________________
    def doCreateFNameList(self):
        # build list of filenames
        list_dates=[]
        list_files=[]
        
        numStart = self.YYYYMMDD_to_Num(self.dlg.editDateStart.date().toString('yyyyMMdd'))
        numEnd = self.YYYYMMDD_to_Num(self.dlg.editDateEnd.date().toString('yyyyMMdd'))
       
        inDir=self.dlg.editInDir.text()
        prefix=self.dlg.editPrefix.text()
        suffix=self.dlg.editSuffix.text()

        for icount in range(numStart, numEnd + 1):
            thisDate = self.Num_to_YYYYMMDD(icount)
            list_dates.append(thisDate)
            list_files.append( os.path.join(inDir, '{}{}{}'.format(prefix, thisDate, suffix)) )

        if len(list_files)==0:
            self.logMsg('There is no date to process. Check input directory and file name: {}YYYYMMDD{}. Please select date, with day=1, 11 or 21.'.format(inDir,self.fname['prefix'], self.fname['prefix']))
            return False
        # check files actually exist
        test=True
        for ii in list_files:
            if not os.path.isfile(ii):
                test=False
                self.logMsg("Missing file: {}".format(ii) )
        # error message and exit
        if test==False:
            self.logMsg('Missing files, please check files existence and consistency with dates', QgsMessageLog.CRITICAL)
            return False
            
        return list_files

    # ___________________
    def doTmpName(self, fname):
        return '{}_{}.tif'.format(fname, random.randint(0,10000))
    # ___________________
    # clip (gdalwarp) the preceding result, then replace it
    def doClip(self):
        inFiles= [ self.dlg.editOutAverage.text(), self.dlg.editOutMinimum.text(), self.dlg.editOutMaximum.text() ]
        inCheck= [ self.dlg.checkAverage.isChecked(), self.dlg.checkMinimum.isChecked(), self.dlg.checkMaximum.isChecked() ]
        inFname= []
        inCRS  = []

        # first create the list of files that need to be opened (depends on user choice)
        for ii, cc in zip(inFiles, inCheck):
            if cc == True: # skip filenames which are not set
                thisFid = gdal.Open(ii, GA_ReadOnly)
                if thisFid is None:
                    self.dlg.logMsg("Could not open file {}".format(ii))
                    return False
                thisCRS = thisFid.GetProjection()
                inFname.append(ii)
                inCRS.append(thisCRS)
                thisFid=None # close file, as we'll need to delete it later on
    
        for thisName, thisCRS in zip(inFname, inCRS):
            ext = self.clipLayer.extent()
            bb  = [ ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum() ]
            # processing.runalg("gdalogr:warpreproject")
            #ALGORITHM: Warp (reproject)
            #INPUT <ParameterRaster>
            #SOURCE_SRS <ParameterCrs>
            #DEST_SRS <ParameterCrs>
            #NO_DATA <ParameterString>
            #TR <ParameterNumber>
            #METHOD <ParameterSelection>
            #RTYPE <ParameterSelection>
            #COMPRESS <ParameterSelection>
            #JPEGCOMPRESSION <ParameterNumber>
            #ZLEVEL <ParameterNumber>
            #PREDICTOR <ParameterNumber>
            #TILED <ParameterBoolean>
            #BIGTIFF <ParameterSelection>
            #TFW <ParameterBoolean>
            #EXTRA <ParameterString>
            #OUTPUT <OutputRaster>
            extraParam = '-te {} {} {} {} -cutline {}'.format(bb[0], bb[1], bb[2], bb[3], self.dlg.editClipShp.text())
            output = self.doTmpName(thisName)
            self.logMsg("input is {}; utput is {}".format(thisName, output))
            self.logMsg("extraParam {}".format(extraParam))
            #METHOD(Resampling method):	0 - near, 1 - bilinear, 2 - cubic, 3 - cubicspline, 4 - lanczos
            #RTYPE(Output raster type): 0 - Byte, 1 - Int16, 2 - UInt16, 3 - UInt32, 4 - Int32, 5 - Float32, 6 - Float64
            #COMPRESS(GeoTIFF options. Compression type): 	0 - NONE, 1 - JPEG, 2 - LZW, 3 - PACKBITS, 4 - DEFLATE
            #BIGTIFF(Control whether the created file is a BigTIFF or a classic TIFF): 0 - , 1 - YES, 2 - NO, 3 - IF_NEEDED, 4 - IF_SAFER
            testproc = processing.runalg('gdalogr:warpreproject',
                          thisName, # input
                          thisCRS, # source crs
                          thisCRS, # dest srs
                          '0', # no data, <parameterString>
                          0, # target resolution: 0=unchanged
                          0, # method: 0, as we are only clipping
                          0, # output raster type
                          2, # compression
                          None, # jpeg compression
                          None, # zlevel
                          None, # predictor
                          None, # tiled
                          None, # bigtiff
                          None, # TFW
                          extraParam, # extra 
                          output)
            if not testproc:
                self.logMsg("Reprojection failed for file {inFileName}")
                return False
     
        return thisName, output
    # ___________________
    def doCompute(self):

        self.logMsg("--- Starting processing ---")
    
        classes=[[0.68, 0.98],[0.50, 0.68],[0.30, 0.50],[0.15, 0.30],[-0.10, 0.15]]
        if self.dlg.checkValReal.isChecked():
            DN2F = [1.0, 0]
        elif self.dlg.checkDNSPOT.isChecked():
            DN2F = [0.004, -0.1]
        elif self.dlg.checkDNPROBA.isChecked():
            DN2F = [0.004, -0.08]
        else:
            self.logMsg("Error: unknown input value conversion factor. Please revise code")
            return False
    
        list_files = self.doCreateFNameList()
        if not list_files:
            self.logMsg("Could not find files matching input criterias on tab 'Input files'. Please revise input directory, suffix, prefix and dates.")
            self.iface.messageBar().pushMessage("CRITICAL", "Could not find files matcing input criterias on tab 'Input files'. Please revise input directory, suffix, prefix and dates.")
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        if len(list_files)==0:
            self.logMsg("no input file, please check inputs.")
            return False

        # let's open all files
        listFID=[]
        for ii in list_files:
            self.logMsg( 'Opening file {}'.format(ii) )
            thisFID = gdal.Open(ii, GA_ReadOnly)
            listFID.append(thisFID)
            
        # get geospatial properties from the first input file
        thisProj = listFID[0].GetProjection()
        thisTrans = listFID[0].GetGeoTransform()
        ns = listFID[0].RasterXSize
        nl = listFID[0].RasterYSize
        format='GTiff'
        options=['compress=lzw']
        
        # let's instantiate the output(s)
        if self.dlg.checkAverage.checkState():
            outFileAVG = self.dlg.editOutAverage.text()
            if self.dlg.checkClassifyAverage.checkState():
                outType=GDT_Byte
            else:
                outType=GDT_Float32
            outDrv = gdal.GetDriverByName(format)
            avgDS = outDrv.Create( outFileAVG, ns, nl, 1, outType, options  )
            avgDS.SetProjection(thisProj)
            avgDS.SetGeoTransform(thisTrans)
       
        if self.dlg.checkMinimum.checkState():
            outFileMIN = self.dlg.editOutMinimum.text()
            if self.dlg.checkClassifyMinimum.checkState():
                outType=GDT_Byte
            else:
                outType=GDT_Float32
            outDrv = gdal.GetDriverByName(format)
            minDS = outDrv.Create( outFileMin, ns, nl, 1, outType, options)
            minDS.SetProjection(thisProj)
            minDS.SetGeoTransform(thisTrans)
        
        if self.dlg.checkMaximum.checkState():
            outFileMAX = self.dlg.editOutMaximum.text()
            if self.dlg.checkClassifyMaximum.checkState():
                outType=GDT_Byte
            else:
                outType=GDT_Float32
            outDrv = gdal.GetDriverByName(format)
            maxDS = outDrv.Create( outFileMax, ns, nl, 1, outType, options)
            minDS.SetProjection(thisProj)
            minDS.SetGeoTransform(thisTrans)

        self.logMsg("Processing with converion factors: {} {}".format(DN2F[0], DN2F[1]))
        if self.dlg.checkAverage.checkState():
            self.logMsg("Average is computed")
        if self.dlg.checkMinimum.checkState():
            self.logMsg("Minimum is computed")
        if self.dlg.checkMaximum.checkState():
            self.logMsg("Maximum is computed")

        data=[]
        
        # parse by line
        for il in range(nl):
            data=[]
            # get the whole time series for this line
            for ifile in listFID:
                thisDataset = numpy.ravel(ifile.GetRasterBand(1).ReadAsArray(0, il, ns, 1).astype(float))
                data.append(thisDataset*DN2F[0] + DN2F[1])
                
            data = numpy.asarray(data)
            avg = data.sum(axis=0) / float(len(listFID))
        
            recoded = numpy.zeros(avg.shape)
            if self.dlg.checkClassifyAverage.checkState():
                # note: do not classify in place
                iClassVal = 0
                for iclasses in classes:
                    iClassVal += 1
                    wrecode = (avg >= iclasses[0]) * (avg < iclasses[1])
                    if wrecode.any():
                        recoded[wrecode]= iClassVal
                avg = recoded
        
            # write outputs
            if self.dlg.checkAverage.checkState():
                avgDS.GetRasterBand(1).WriteArray( avg.reshape(1,ns), 0, il )

        # close files
        for ii in listFID:
            ii = None
        if self.dlg.checkAverage.checkState():
            avgDS = None
        if self.dlg.checkMinimum.checkState():
            minDS = None
        if self.dlg.checkMaximum.checkState():
            maxDS = None        
        
        return True
    # ___________________
    def run(self):
        # initialise GUI
        self.doInitGui()
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
            computeOK=False
            computeOK = self.doCompute()
            if computeOK and self.dlg.checkClipShp.isChecked():
                returnClip = self.doClip()
            if returnClip==False:
                self.logMsg("Error in processing. Exit.")
            else:
                # replace original with clipped file
                try:
                    os.remove( returnClip[0] )
                    os.rename( returnClip[1], returnClip[0] )
                except OSError:
                    self.logMsg("Could not replace temporary file {} with its clipped version {}".format(returnClip[0], returnClip[1]))
                    return False
                
                self.iface.addRasterLayer(self.dlg.editOutAverage.text(), 'Average')
