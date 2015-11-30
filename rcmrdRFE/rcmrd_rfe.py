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
import processing
# gdal
from osgeo import gdal
from osgeo.gdalconst import *
# Import the code for the dialog
from rcmrd_rfe_dialog import rcmrdRFEDialog
import os.path
import random
import subprocess
# for computing natural_breaks distribution
#from pysal.esda.mapclassify import Natural_Breaks

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
        self.menu = self.tr(u'&RCMRD: rainfall erosivity')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'RCMRD: RFE')
        self.toolbar.setObjectName(u'RCMRD: RFE')

        # default values
        #self.inDir='/Users/bruno/Desktop/mesa_data/input/Rainfall'
        #self.dateStart={'day':1,'month':2,'year':2015}
        #self.dateEnd={'day':1,'month':10,'year':2015}
        
        self.clipLayer = None # the layer loaded in memory
        # a global storing temp files names, before clipping
        self.intermediateFiles={'RFE':'', 'RFD':'', 'RFI':''} # empty means no file is selected
        
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
        QgsMessageLog.logMessage(msg, tag='RCMRD Rainfall Erosivity',level=errorLvl)
        
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
        dialog = QFileDialog()
        dirName = dialog.getExistingDirectory(self.dlg, self.tr('Choose directory'), os.path.expanduser("~"))
        if dirName:
            if dirSelector=='inDir':
                self.dlg.editInputDir.setText(dirName)
    # ___________________
    def doOpenFile(self, selector):
        text = {'clipShp': 'clipping shapefile'}
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
    # ___________________
    def doSaveFname(self, selector):
    
        text={'rfe':'Rainfall Erosivity', 'rfd':'Rainfall Depth', 'rfi':'Rainfall Intensity'}
        dialog = QFileDialog()
        saveFname = dialog.getSaveFileName(self.dlg, self.tr("Define a file name to save {}".format(text[selector])), os.path.expanduser("~"))
        if saveFname:
            if selector=='rfd':
                self.dlg.editRFD.setText(saveFname)
            if selector=='rfi':
                self.dlg.editRFI.setText(saveFname)
            if selector=='rfe':
                self.dlg.editRFE.setText(saveFname)
    # ___________________
    # create the list of files using input dir, prefix, suffix, and date loop (assuming day in 1, 01, 21)
    # return list_files or False
    def doCreateFNameList(self):
        list_files=[]
        list_dates=[]
        numStart = self.YYYYMMDD_to_Num( self.dlg.editDateStart.date().toString('yyyyMMdd') )
        numEnd = self.YYYYMMDD_to_Num( self.dlg.editDateEnd.date().toString('yyyyMMdd') )
       
        inDir=self.dlg.editInputDir.text()

        for icount in range(numStart, numEnd + 1):
            thisDate = self.Num_to_YYYYMMDD(icount)
            list_dates.append(thisDate)
            list_files.append( os.path.join(inDir, '{}{}{}'.format(self.dlg.editPrefix.text(), thisDate, self.dlg.editSuffix.text() )) )

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
            self.logMsg('Missing files, please check files existence and consistency with dates')
            return False
            
        return list_files
    # ___________________
    def doCompute(self):
    
        self.logMsg("--- Processing is starting ---")
        # build list of filenames
        intensityThreshold = self.dlg.intensityThreshold.value()
        WRD = float(self.dlg.valueWRD.value())
        WRI = float(self.dlg.valueWRI.value())
        
        list_files = self.doCreateFNameList()
        if not list_files:
            self.logMsg("Could not find files matching input criterias on tab 'Input files'. Please revise input directory, suffix, prefix and dates.")
            self.iface.messageBar().pushMessage("CRITICAL", "Could not find files matching input criterias on tab 'Input files'. Please revise input directory, suffix, prefix and dates.")
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
            
        # let's instantiate the output
        thisProj = listFID[0].GetProjection()
        thisTrans = listFID[0].GetGeoTransform()
        ns = listFID[0].RasterXSize
        nl = listFID[0].RasterYSize
        format='GTiff'
        options=['compress=lzw']
        outType=GDT_Float32
        outDrv = gdal.GetDriverByName(format)

        outFileRFE = self.doTmpName( self.dlg.editRFE.text() )
        self.intermediateFiles['RFE'] = outFileRFE
        outFileRFD = self.doTmpName( self.dlg.editRFD.text() )
        self.intermediateFiles['RFD'] = outFileRFD
        outFileRFI = self.doTmpName( self.dlg.editRFI.text() )
        self.intermediateFiles['RFI'] = outFileRFI
        outDs = outDrv.Create( outFileRFE, ns, nl, 1, outType, options  )
        outDsRFD = outDrv.Create( outFileRFD, ns, nl, 1, outType, options)
        outDsRFI = outDrv.Create( outFileRFI, ns, nl, 1, outType, options)
        outDs.SetProjection(thisProj)
        outDs.SetGeoTransform(thisTrans)
        outDsRFD.SetProjection(thisProj)
        outDsRFD.SetGeoTransform(thisTrans)
        outDsRFI.SetProjection(thisProj)
        outDsRFI.SetGeoTransform(thisTrans)

        data=[]

        # display processing info
        self.logMsg('Processing with Intensity weight={}, Depth weight={}, and accumulation threshold={}'.format(WRI, WRD, intensityThreshold))
        
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
            wLow = data < intensityThreshold
            if wLow.any():
                data[wLow] = 0
            sumIntensity = data.sum(axis=0)
            
            sumErosivity = WRI*sumIntensity + WRD* sumDepth

            # write outputs
            outDs.GetRasterBand(1).WriteArray(sumErosivity.reshape(1,ns), 0, il)
            outDsRFI.GetRasterBand(1).WriteArray(sumIntensity.reshape(1,ns),0,il )
            outDsRFD.GetRasterBand(1).WriteArray(sumDepth.reshape(1,ns),0,il)

        # close files
        for ii in listFID:
            ii = None
        outDs = None
        outDsRFI = None
        outDsRFD = None

        return True
    # ___________________
    def doTmpName(self, fname):
        return '{}_{}.tif'.format(fname, random.randint(0,10000))
    # ___________________
    def doClipShell(self):
        inFiles  = [ self.intermediateFiles['RFE'], self.intermediateFiles['RFD'], self.intermediateFiles['RFI'] ]
        outFiles = [ self.dlg.editRFE.text(), self.dlg.editRFD.text(), self.dlg.editRFI.text() ]
        inFname  = []
        inCRS    = []
        outFname = []

        # first create the list of files that need to be opened (depends on user choice)
        for ii, oo in zip(inFiles, outFiles):
            thisFid = gdal.Open(ii, GA_ReadOnly)
            if thisFid is None:
                self.dlg.logMsg("Could not open file {}".format(ii))
                return False
            thisCRS = thisFid.GetProjection()
            inFname.append(ii)
            inCRS.append(thisCRS)
            thisFid = None # close file, as we'll need to delete it later on
            outFname.append(oo)
    
        ext = self.clipLayer.extent()
        bb  = [ ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum() ]
        extraParam = '-te {} {} {} {} -cutline "{}" -crop_to_cutline '.format(bb[0], bb[1], bb[2], bb[3], self.dlg.editClipShp.text())
    
        command='gdalwarp -of GTiff -co "compress=lzw" -dstnodata 0 {} "{}" "test_{}"'.format(extraParam, inFname[0], outFname[0])
    
        result=[]
        for thisName, thisCRS, thisOut in zip(inFname, inCRS, outFname):
            command='gdalwarp -of GTiff -co "compress=lzw" -dstnodata 0 {} "{}" "{}"'.format(extraParam, thisName, thisOut)
            self.logMsg(command)
            self.logMsg("extraParam {}".format(extraParam))
            thisProc = subprocess.Popen(command, shell=False)
            thisProc.wait()
            result.append(thisProc) # for furter analysis, if needed
        return True
        
    # ___________________
    # this version is for using plugin processing
    # input: self.intermediateFiles
    # output: filenames as defined in the interface
    def doClip(self):
        inFiles  = [ self.intermediateFiles['RFE'], self.intermediateFiles['RFD'], self.intermediateFiles['RFI'] ]
        outFiles = [ self.dlg.editRFE.text(), self.dlg.editRFD.text(), self.dlg.editRFI.text() ]
        inFname  = []
        inCRS    = []
        outFname = []

        # first create the list of files that need to be opened (depends on user choice)
        for ii, oo in zip(inFiles, outFiles):
            thisFid = gdal.Open(ii, GA_ReadOnly)
            if thisFid is None:
                self.dlg.logMsg("Could not open file {}".format(ii))
                return False
            thisCRS = thisFid.GetProjection()
            inFname.append(ii)
            inCRS.append(thisCRS)
            thisFid = None # close file, as we'll need to delete it later on
            outFname.append(oo)
    
        ext = self.clipLayer.extent()
        bb  = [ ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum() ]
        for thisName, thisCRS, thisOut in zip(inFname, inCRS, outFname):
            extraParam = '-dstnodata 0 -te {} {} {} {} -cutline "{}" -crop_to_cutline '.format(bb[0], bb[1], bb[2], bb[3], self.dlg.editClipShp.text())
            self.logMsg("extraParam {}".format(extraParam))
            testproc = processing.runalg('gdalogr:warpreproject',
                          thisName, # input
                          thisCRS, # source crs
                          thisCRS, # dest srs
                          '0', # no data, <parameterString>
                          0, # target resolution: 0=unchanged
                          0, # method: 0, as we are only clipping
                          5, # output raster type
                          2, # compression
                          None, # jpeg compression
                          None, # zlevel
                          None, # predictor
                          None, # tiled
                          None, # bigtiff
                          None, # TFW
                          extraParam, # extra 
                          thisOut)
            if not testproc:
                self.logMsg("Reprojection failed for file {inFileName}")
                return False
     
        return True
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
        #self.dlg.editInputDir.clear()
        #self.dlg.editInputDir.setText( os.path.expanduser("~") )
        # Do not init the input, so they keep memory of the preceeding choice
        
        self.dlg.buttonDir.clicked.connect(lambda: self.doOpenDir('inDir'))
        self.dlg.buttonDirRFD.clicked.connect(lambda: self.doSaveFname('rfd'))
        self.dlg.buttonDirRFE.clicked.connect(lambda: self.doSaveFname('rfe'))
        self.dlg.buttonDirRFI.clicked.connect(lambda: self.doSaveFname('rfi'))

        # prefix
        self.dlg.editPrefix.clear()
        # suffix
        self.dlg.editSuffix.setText('_rfe.tif')
        
        # signals for clipShp widgets
        self.dlg.checkClipShp.stateChanged.connect( self.doClipShpWidgetsUpdate )
        self.dlg.buttonClipShp.clicked.connect( (lambda: self.doOpenFile('clipShp') ) )
    # ____________________
    # return False if any test is not past
    def doCheckReady(self):
        # Check input directory
        inDir=self.dlg.editInputDir.text()
        if not os.path.isdir(inDir):
            self.logMsg('{} is not a directory. Please correct input directory, in "Input files" tab.'.format(inDir), QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        # check input files
        list_files = self.doCreateFNameList()
        if list_files == False:
            self.logMsg('Missing input files. Please check input directory, prefix, suffix and dates definition in "Input files" tab.', QgsMessageLog.CRITICAL)
        # check ouput file
        if self.dlg.editRFD.text() == '':
            self.logMsg('Please define an output file name for Rainfall Depth, in "Output files" tab.', QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        if self.dlg.editRFI.text() == '':
            self.logMsg('Please define an output file name for Rainfall Intensity, in "Output files" tab.', QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        if self.dlg.editRFE.text() == '':
            self.logMsg('Please define an output file name for Rainfall Erosivity, in "Output files" tab.', QgsMessageLog.CRITICAL)
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
            
        # check output files are all different
        if self.dlg.editRFD.text() == self.dlg.editRFI.text():
            self.logMsg("Error: RFD and RFI files are identical. Please revise 'Output files' tab.")
            self.iface.messageBar().pushMessage("Error: RFD and RFI files are identical. Please revise 'Output files' tab.")
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        if self.dlg.editRFD.text() == self.dlg.editRFE.text():
            self.logMsg("Error: RFD and RFE files are identical. Please revise 'Output files' tab.")
            self.iface.messageBar().pushMessage("Error: RFD and RFE files are identical. Please revise 'Output files' tab.")
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
        if self.dlg.editRFI.text() == self.dlg.editRFE.text():
            self.logMsg("Error: RFI and RFE files are identical. Please revise 'Output files' tab.")
            self.iface.messageBar().pushMessage("Error: RFI and RFE files are identical. Please revise 'Output files' tab.")
            self.dlg.tabs.setCurrentWidget(self.dlg.tabMessages)
            return False
            
        return True
    #___________________
    # classify the image, using natural break
    # images can be large, and the analysis to take a lot of time and memory: only 1/4 pixels and lines are used.
    
    def doClassify(self, fname):
        # read the image: 1/NSkip lines, 1/NSkip column
        fid = gdal.Open(fname, GA_ReadOnly)
        ns = fid.RasterXSize
        nl = fid.RasterYSize
        data=[]
        if min(ns, nl)> 3000:
            NSkip=12
        elif min(ns,nl)> 2000:
            NSkip=10
        elif min(ns,nl) > 1000:
            NSkip=8
        else:
            NSkip=6
        
        self.logMsg("Classification: reading input")
        for il in range(0, nl, NSkip):
            thisData = numpy.ravel( fid.GetRasterBand(1).ReadAsArray(0, il, ns, 1) )
            data.append(thisData[range(0, ns, NSkip)])
        fid = None
        # compute natural breaks: the object must be unidimensional, and have a copy function
        self.logMsg("Classification: searching for natural_breaks")
        natBreaks = Natural_Breaks(numpy.ravel(data), k=5)
        bins=[0]
        bins.extend(natBreaks.bins)
        len_bins = len(bins)
        data = None
        natBreaks = None
        # write out results
        self.logMsg("Natural breaks for {}".format(fname))
        self.logMsg("Classification: recoding")
        for ii in range(1,len_bins):
            self.logMsg("Class {}: {}".format(ii, bins[ii]))
        # instead of duplicating the image in memory, let's do now the work line by line: memory friendly
        tempName = '{}_naturalBreaks_{}.tif'.format( fname, random.randint(1,100000) )
        fid = gdal.Open(fname, GA_ReadOnly)
        ns = fid.RasterXSize
        nl = fid.RasterYSize
        outDrv = gdal.GetDriverByName('GTiff')
        outDs = outDrv.Create(tempName, ns, nl, 1, GDT_Byte, ['compress=LZW'])
        outDs.SetProjection(fid.GetProjection())
        outDs.SetGeoTransform(fid.GetGeoTransform())
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

        fid=None
        outDs=None
        # mv temp file into initial file
        self.logMsg("Classification: mv file")
        try:
            os.remove(fname)
            os.rename(tempName, fname)
        except OSError:
            self.logMsg("Could not replace temporary file {} with its classification {}".format(fname, tempName))
            return False
                
        return True
    # ___________________
    def doReplaceFiles(self,files):
        try:
            os.remove(files[0])
            os.rename(files[1], files[0])
        except OSError:
            self.logMsg("Could not replace temporary file {} with its clipped version {}".format(files[0], files[1]))
            return False
        return True
    # ____________________
    def run(self):
        # initialise GUI
        self.doInitGui()
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        okToGo=False
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
            if not computeOK:
                self.logMsg("Error in processing. Exit.")
            #    return False
            #computeOK = self.doClassify( self.intermediateFiles['RFE'] )
            #if not computeOK:
            #    self.logMsg('Could not classify Erosivity image. All process stopped.', QgsMessageLog.CRITICAL)
                return False
            else:
                if self.dlg.checkClipShp.isChecked():
                    computeOK = self.doClip()
                    if not computeOK:
                        self.logMsg("Problem when clipping results")
                        return False
                else: # rename files
                    inFiles  = [ self.intermediateFiles['RFE'], self.intermediateFiles['RFD'], self.intermediateFiles['RFI'] ]
                    outFiles = [ unicode(self.dlg.editRFE.text()), unicode(self.dlg.editRFD.text()), unicode(self.dlg.editRFI.text()) ]
                    try:
                        for iiIn, iiOut in zip(inFiles, outFiles):
                            os.rename(iiIn, iiOut)
                    except OSError:
                        self.logMsg("Error when tying to create final file {}. Please use intermediate file {} instead".format(iiOut, iiIn), QgsMessageLog.CRITICAL)
                        self.dlg.setCurrentWidget(self.dlg.tabMessages)
                if computeOK:
                    self.iface.addRasterLayer(unicode(self.dlg.editRFE.text()), 'Rainfall erosivity')
                    self.iface.addRasterLayer(unicode(self.dlg.editRFI.text()), 'Rainfall intensity')
                    self.iface.addRasterLayer(unicode(self.dlg.editRFD.text()), 'Rainfall depth')
