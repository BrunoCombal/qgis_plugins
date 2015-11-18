# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RCMRD_LandDegr
                                 A QGIS plugin
 Compute land degradation indices
                              -------------------
        begin                : 2015-10-16
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Bruno Combal, MESA
        email                : bruno.combal@gmail.com
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.core import *
# gdal
import processing
from osgeo import osr, gdal
from osgeo.gdalconst import *
import numpy
import random
#import tempfile
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
        self.WrkDir = os.path.join( os.path.expanduser("~"), "qgis_rcmrdplugin" )
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
        self.raster_list = []
        self.dictReproj = None

        self.listIDInputs={}
        self.listIDWeightsPotential={}
        self.listIDWeightsActual={}

        SettingsOrganisation='RCMRD_QGIS'
        SettingsApplication='RCMRD_LandDegr'

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
            whats_this=self.tr(u'Compute RCMRD LDIM'),
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

    # ____________________
    def logMsg(self, msg, errorLvl = QgsMessageLog.INFO):
        QgsMessageLog.logMessage( msg, tag='RCMRD Land Degradation', level=errorLvl)
        
        prepend=''
        if errorLvl==QgsMessageLog.WARNING:
            self.iface.messageBar().pushMessage("WARNING", msg)
            prepend="Warning! "
        if errorLvl==QgsMessageLog.CRITICAL:
            self.iface.messageBar().pushMessage("CRITICAL",msg)
            prepend="Critical error! "
        self.dlg.logTextDump.append(prepend + msg)
    #  ____________________
    # Business logic functions and methods
    # ____________________
    # returns uniq of an array, preserve order
    def uniquify(self, seq):
        noDupes = []
        [noDupes.append(i) for i in seq if not noDupes.count(i)]
        return noDupes
    # ____________________
    # Get target extent, in geographical coordinates
    def getTE(self):
        xmin=float(self.dlg.ROIWestEdit.text())
        xmax=float(self.dlg.ROIEastEdit.text())
        ymin=float(self.dlg.ROISouthEdit.text())
        ymax=float(self.dlg.ROINorthEdit.text())
        return [xmin, ymin, xmax, ymax]
    # _____________________
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
    # _____________________
    # doInitDir: if the directory does not exist: create it
    def doInitDir(self, thisDir):
        if os.path.isdir(thisDir):
            return True
        os.makedirs(thisDir)
    # _____________________
    def doTempFile(self, prefix='', suffix='', dir=''):
        idTag = random.randint(10000, 99999)
        return os.path.join(dir, prefix + '_' + str(idTag) + suffix)
        
        # ____________________
    # search for layer name, returns filename
    def retrieveFromName(self, name):
        for ii in raster_list:
            if ii.name()==name: return ii.source()
        return False
    # ____________________
    def getInputFiles(self):

        inFiles=[]
        for kk, ii in self.listIDInputs.iteritems():
            thisFile = self.retrieveFromName( ii )
            if thisFile==False:
                self.logMsg("Could no retrieve file {}".format(  ))
                return False
            else:
                inFiles.append(thisFile)
                self.dictInput[ii]=thisFile
                
        return thisFile

    # _____________________    
    # doResample: resample the inputs to a common projection and resolution, will crop images
    # images saved into the working directory
    # note: to read documentation about an algorithm: import processing; processing.alghelp("gdalogr:warpreproject")
    def doResample(self, inFileName, output):
        self.doInitDir(self.WrkDir)

        # for now, dst is hard coded
        #inCRS = QgsCoordinateReferenceSystem(4326) # actually, must be read from the input file
        newCRS = QgsCoordinateReferenceSystem()
        #newCRS.createFromProj4('+proj=aea +lat_1=18 +lat_2=-4 +lat_0=11 +lon_0=25 +x_0=37.5 +y_0=11')
        newCRS.createFromSrid(4326)
        if not newCRS.isValid():
            self.logMsg("The projection definition is not valid. Exit", QgsMessageLog.CRITICAL)
            return False

        # see: https://docs.qgis.org/2.6/en/docs/user_manual/processing_algs/gdalogr/gdal_projections/warpreproject.html
        # inFileName = self.raster_list[self.dlg.comboVegetationIndex.currentIndex()].source()
        self.logMsg("input file " + inFileName)
        inFID = gdal.Open(inFileName, GA_ReadOnly)
        inCRS = inFID.GetProjection()
        inTrans = inFID.GetGeoTransform()
        for ii in inTrans:
            QgsMessageLog.logMessage("Trans " + str(ii))
        # for now, we only resample 1 dataset, to be placed in a loop later on
        thisTE = self.getTE()
        extraParam = "-te {} {} {} {}".format(thisTE[0], thisTE[1], thisTE[2], thisTE[3])
        method = 0 # because we resample thematic layers
        # rtype 0: Byte, 1: int16, 2: uint16, 3:uint32, 4: int32, 5: Float32, 6: Float54
        
        self.logMsg("Reprojection parameters: ")
        self.logMsg("input file: "+ inFileName)
        self.logMsg("input CRS: "+inCRS)
        self.logMsg("output CRS: "+newCRS.toProj4())
        self.logMsg("method: "+ str(method) )
        self.logMsg("rtype: " + str(self.ParseType("Float32")) )
        self.logMsg("outfile: " + output)
     
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

        #METHOD(Resampling method):	0 - near, 1 - bilinear, 2 - cubic, 3 - cubicspline, 4 - lanczos
        #RTYPE(Output raster type): 0 - Byte, 1 - Int16, 2 - UInt16, 3 - UInt32, 4 - Int32, 5 - Float32, 6 - Float64
        #COMPRESS(GeoTIFF options. Compression type): 	0 - NONE, 1 - JPEG, 2 - LZW, 3 - PACKBITS, 4 - DEFLATE
        #BIGTIFF(Control whether the created file is a BigTIFF or a classic TIFF): 0 - , 1 - YES, 2 - NO, 3 - IF_NEEDED, 4 - IF_SAFER
        testproc = processing.runalg('gdalogr:warpreproject',
                          inFileName, # input
                          inCRS, # source ss
                          newCRS.toProj4(), # dest srs
                          '', # no data, <parameterString>
                          0, # target resolution: 0=unchanged
                          0, # method: tematic layers
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
                       
        return True
    # ____________________
    def doIndices(self):
    
        # open reprojected files
        fid={}
        for id, layerName in self.listIDInputs.itermitems():
            thisFile = self.dictReproj[ layerName ]
            fid[id] = gdal.Open(thisFile, GA_ReadOnly)
        
        # create ouputs
        ns = fid['VGT'].RasterXSize
        nl = fid['VGT'].RasterYSize
        projection = fid['VGT'].GetProjection()
        geotrans = fid['VGT'].GetGeoTransform()
        outDrv = gdal.GetDriverByName('GTiff')
        outFID = {}
        outFID['Actual'] = outDrv.Create( self.dlg.editOutALDI.text(), ns, nl, 1, GDT_Byte )
        outFID['Potential'] = outDrv.Create( self.dlg.editOutPLDI.text(), ns, nl, 1, GDT_Byte )
        
        # compute indicators for each line
        for il in range(nl):
            data={}
            outData = {}
            for id in self.listIDInputs:
                data['id'] = numpy.ravel( gdal.GetRasterBand(1).ReadAsArray(0,il, ns, 1) )
                
            # let's compute actual LDIM
            dataActual=numpy.zeros(ns)
            for ii, ww in self.listIDWeightsActual:
                dataActual += ww * data[ii]
                
            dataPotential = numpy.zeros(ns)
            for ii, ww in self.listIDWeightsPotential:
                dataPotential += ww * data[ii]
                
            # save lines
            outFID['Actual'].GetRasterBand(1).WriteArray( dataActual.reshape(1,ns), 0, il)
            outFID['Potential'].GetRasterBand(1).WriteArray( dataPotential.reshape(1,ns), 0, il)
            
        return True
        
    # ____________________
    # Run business logic
    # 1./ reproject/resample input files, save in tmp files
    # 2./ compute indices, per pixel, using weights, save in output files
    # Will exit on any error, reports for errors
    def doProcessing(self):
        # Inputs are reprojected and resampled
        listInput = getInputFiles()
        if listInput == False:
            self.logMsg("Missing input files, processing impossible")
            return False
        for thisFName in listInput:
            self.logMsg("Resampling and reprojection file {}".format(thisFName))
            output = self.doTempFile('reproject', '.tif', self.WrkDir)
            self.dictReproj['thisFName']=output
            if self.doResample(thisFName, output) == False:
                self.logMsg("Reprojection failure for {}".format(thisFName))
                return False
        
        if self.doIndices() == False:
            self.logMsg("Error in processing indices")
            return False
        
        return True
    # ____________________    
    def doCheckToGo(self):
        if (self.selectedRoi) is None:
            self.logMsg("Please choose a region, in the 'Settings' tab.")
            self.logTextDump("Please choose a region, in the 'Settings' tab.")
            self.dlg.tabWidget.setCurrentWidget(tabLog)
            return False
            
        # check all files are different
        listFName=[ii.source() for ii in raster_list]
        if self.uniquify(listFName) != listFName:
            self.logMsg("Input files must be different. Please revise inputs in 'Input files' tab.", QgsMessageLog.CRITICAL)
            self.iface.messageBar.pushMessage("CRITICAL","Error: Input files must be different. Please revise inputs in 'Input files' tab.")

        self.listIDInputs={'VGT':self.dlg.comboVegetationIndex.text(),
            'RFE':self.dlg.comboRainfallErosivity.text(),
            'PopDens':self.dlg.comboPopDensity.text(),
            'SoilErod':self.dlg.comboSoilErodibility.text(),
            'SlopeLF':self.dlg.comboSlopeLF.text() }
            
        self.listIDWeightsPotential={'RFE': self.dlg.spinPotRFE.value(),
            'PopDens': self.dlg.spinPotPopDens.value(),
            'SoilErod': self.dlg.spinPotSoilErod.value(),
            'SlopeLF': self.dlg.spinPotSlopeLF.value()}
            
        self.dlg.listIDWeightsActual={'VGT':self.dlg.spinActVGT.value(),
            'RFE': self.dlg.spinActRFE.value(),
            'PopDens': self.dlg.spinActPopDens.value(),
            'SoilErod': self.dlg.spinActSoilErod.value(),
            'SlopeLF': self.dlg.spinActSlopeLF.value()}
            
        return True

    # _____________________
    def getShpBB(self):

        layer = QgsVectorLayer( self.dlg.editSHPName.text(), "Mask", 'ogr')
        if not layer.isValid():
            print "Layer failed to load!"
        # open shp
        feature.geometry().boundingBox().toString()
    # _____________________
    def displayRoiValues(self):
        if self.dlg.comboChooseArea.currentIndex() is None:
            return
        elif self.dlg.comboChooseArea.currentIndex() == -1:
            self.dlg.RoiWestEdit.clear()
            self.dlg.RoiEastEdit.clear()
            self.dlg.RoiSouthEdit.clear()
            self.dlg.RoiNorthEdit.clear()
        else:
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
    # _____________________
    # add a filename to the list of opened files
    # anf move the index to the last opened file
    def openFile(self, name):
        fname = QFileDialog.getOpenFileName(self.dlg, self.tr("Open raster file"))
        if fname:
            if name=='Vegetation Index':
                self.dlg.comboVegetationIndex.addItem(fname)
                self.dlg.comboVegetationIndex.setCurrentIndex( self.dlg.comboVegetationIndex.count()-1 )
            elif name=='Rainfall Erosivity':
                self.dlg.comboRainfallErosivity.addItem(fname)
                self.dlg.comboRainfallErosivity.setCurrentIndex( self.dlg.comboRainfallErosivity.count()-1 )
            elif name=='Population Density':
                self.dlg.comboPopDensity.addItem(fname)
                self.dlg.comboPopDensity.setCurrentIndex( self.dlg.comboPopDensity.count()-1 )
            elif name=='Slope LF':
                self.dlg.comboSlopeLF.addItem( fname)
                self.dlg.comboSlopeLF.setCurrentIndex( self.dlg.comboSlopeLF.count()-1 )

    # ____________________
    def doInitGUI(self):
    
        self.raster_list = []
        self.dictInput = {}
        self.dictReproj = {}
    
        # clear all widgets first
        self.dlg.comboChooseArea.clear()
        self.dlg.comboVegetationIndex.clear()
        self.dlg.comboPopDensity.clear()
        self.dlg.comboRainfallErosivity.clear()
        self.dlg.comboSlopeLF.clear()
        self.dlg.comboSoilErodibility.clear()
        self.dlg.logTextDump.clear()

        # initialise lineEditWrkDir with self.WrkDir
        self.dlg.lineEditWrkDir.clear()
        self.dlg.lineEditWrkDir.setText(self.WrkDir)

        # force opening on the "Help" tab
        self.dlg.tabWidget.setCurrentWidget(self.dlg.tabHelp)
    # ____________________
    def run(self):
        """Set up the interface content and call business-logic functions"""

        self.doInitGui()

        self.dlg.logTextDump.append("Initialising...")
        # setup "settings" tools. ROI are defined with xMin, yMin, xMax, yMax
        self.dlg.comboChooseArea.addItems( [ ii["name"] for ii in self.roiDefinitions ] )
        for ii in self.roiDefinitions:
            self.dlg.logTextDump.append( ii["name"] )
        self.dlg.comboChooseArea.currentIndexChanged.connect(self.displayRoiValues)
        self.dlg.comboChooseArea.setCurrentIndex(-1)
        self.displayRoiValues()

        # setup input files
        self.dlg.logTextDump.append("Scanning loaded files")
        layers = self.iface.legendInterface().layers()
        vector_list = []
        self.raster_list=[] # reset to 0 each time the plugin is called
        
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
                self.raster_list.append(layer)

        # Assign the pre-loaded rasters and vectors to the interface objects
        for ii in self.raster_list:
            self.dlg.comboVegetationIndex.addItem(ii.name())
            self.dlg.comboPopDensity.addItem(ii.name())
            self.dlg.comboRainfallErosivity.addItem(ii.name())
            self.dlg.comboSlopeLF.addItem(ii.name())
            self.dlg.comboSoilErodibility.addItem(ii.name())

        # connect the file chooser function to the buttons
        self.dlg.buttonVegetationIndex.clicked.connect(lambda: self.openFile('Vegetation Index'))
        self.dlg.buttonRainfallErosivity.clicked.connect(lambda: self.openFile('Rainfall Erosivity'))
        self.dlg.buttonPopDensity.clicked.connect(lambda: self.openFile('Population Density'))
        self.dlg.buttonSlopeLF.clicked.connect(lambda: self.openFile('Slope LF'))

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
        #self.dlg.logTextDump.append("Application running.")
        #self.iface.messageBar().pushMessage("Info","Running")

        # See if OK was pressed
        if result:
            # then run processings
            self.doProcessing()
            self.iface.messageBar().pushMessage("Info","result is true")
            #QgsMessageLog.logMessage("Value is " + str(self.dlg.data1.value()))
