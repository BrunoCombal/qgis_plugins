# -*- coding: utf-8 -*-
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFile, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.core import *
import os, os.path


# ___________________
def logMsg(self, msg, errorLvl=QgsMessageLog.INFO):
    QgsMessageLog.logMessage(msg, tag='RCMD Time Series',level=errorLvl)
        
    prepend=''
    if errorLvl==QgsMessageLog.WARNING:
        self.iface.messageBar().pushMessage("WARNING", msg)
        prepend="Warning! "
    if errorLvl==QgsMessageLog.CRITICAL:
        self.iface.messageBar().pushMessage("CRITICAL",msg)
        prepend="Critical error! "
    self.dlg.logTextDump.append(prepend + msg)

# __________
# ref.: http://pythoncentral.io/pyside-pyqt-tutorial-the-qlistwidget/
def updateBulletinList(widgetList):
	for ii in range(100):
		widgetList.addItem("Coucou {}".format(ii))

