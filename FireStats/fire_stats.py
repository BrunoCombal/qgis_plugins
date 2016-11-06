# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FireStats
                                 A QGIS plugin
 Compute fire detections statistics on a shapefile
                              -------------------
        begin                : 2016-10-12
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Bruno Combal
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
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QLabel, QPixmap
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from fire_stats_dialog import FireStatsDialog
import fireStatsTools, fireStatsGUITools
import ConfigParser
import ast
import os.path


class FireStats:
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
            'FireStats_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Fire Statistics')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'FireStats')
        self.toolbar.setObjectName(u'FireStats')

        self.configuration = ConfigParser.ConfigParser()
        self.thisConf = {}

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
        return QCoreApplication.translate('FireStats', message)


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

        # Create the dialog (after translation) and keep reference
        self.dlg = FireStatsDialog()

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
    # ___________________
    def logMsg(self, msg, errorLvl=QgsMessageLog.INFO):
        QgsMessageLog.logMessage(msg, tag='Fire stats',level=errorLvl)
            
        prepend=''
        if errorLvl==QgsMessageLog.WARNING:
            self.iface.messageBar().pushMessage("WARNING", msg)
            prepend="Warning! "
        if errorLvl==QgsMessageLog.CRITICAL:
            self.iface.messageBar().pushMessage("CRITICAL",msg)
            prepend="Critical error! "
        #self.dlg.logTextDump.append(prepend + msg)

    # __________
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/FireStats/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Fire Stats'),
            callback=self.run,
            parent=self.iface.mainWindow())

    # __________
    def doInitGui(self):
        # define icon
        pic = QLabel(self.dlg)
        pic.setGeometry(5, 5, 24, 24)
        #use full ABSOLUTE path to the image, not relative
        pic.setPixmap(QPixmap(self.plugin_dir + "/icon.png"))

        # update database
        self.dlg.updateDBButton.clicked.connect( lambda: self.doDBProc('update') )
        # regenerate database
        self.dlg.regenerateDBButton.clicked.connect( lambda: self.doDBProc('regenerate') )

        # run update of bulletins lists
        fireStatsTools.updateBulletinList(self.dlg.bulletinsList)
        self.dlg.openSelectedBulletinButton.clicked.connect( lambda: self.openSelectedBulletin('inDir') )

        # read config file if it exists, else set defaults
        self.logMsg( os.path.join(os.getcwd(), 'default.cfg') )
        self.configuration.read( [ os.path.join(self.plugin_dir, 'user_config.cfg') , os.path.join(self.plugin_dir, 'default.cfg') ] )
        # ast.literal_eval(self.configuration.items('fire stats')[1][1])
        for ii in self.configuration.items('fire stats'):
            if ii[0]=='fire_derived':
                self.thisConf[ ii[0] ] = ast.literal_eval( ii[1] )
            elif ii[0]=='season':
                self.thisConf[ ii[0] ] = ast.literal_eval( ii[1] )
            else:
                self.thisConf[ ii[0] ] = ii[1]

        # update tab "Configuration"
        fireStatsGUITools.updateConfTab(self.dlg, self.thisConf)
    # __________
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Fire Statistics'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # __________
    def doDBProc(self, selector):

        refRaster = r'/data/modis-firms/1day/MESA_JRC_modis-firms_1day_20150101_SPOTV-Africa-1km_v5.0.tif'
        refIdRaster = r'/data/tmp/test_rasterID.tif'

        print 'Entering procedure'
        if selector=='update':
            print 'doing update'
            detectionRaster = r'/data/modis-firms/1day/MESA_JRC_modis-firms_1day_20150101_SPOTV-Africa-1km_v5.0.tif'
            countResult = fireStatsTools.doCountPerPolygonId(refIdRaster, detectionRaster)            
            print countResult

        if selector=='regenerate':
            print 'doing regenerate'
            shpFile=r'/data/g2015_2012_0/g2015_2012_0_subsetAfrica_simplified.shp'
            outRaster=r'/data/tmp/test_rasterID.tif'
            fireStatsTools.doBurnShpToRaster(shpFile, 'ADM0_CODE', refRaster, outRaster)

            detectionRaster = r'/data/modis-firms/1day/MESA_JRC_modis-firms_1day_20150101_SPOTV-Africa-1km_v5.0.tif'
            countResult = fireStatsTools.doCountPerPolygonId(outRaster, detectionRaster)

        print '--- end ---'
        print

    # __________
    def openSelectedBulletin(self, dirSelector):
        dialog = QFileDialog()
        dirName = dialog.getExistingDirectory(self.dlg, self.tr('Choose directory'), os.path.expanduser("~") )
        if dirName:
            if dirSelector=='inDir':
                self.editInDir.setText(dirName)

    # __________
    def run(self):
        """Run method that performs all the real work"""
        self.doInitGui()
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
