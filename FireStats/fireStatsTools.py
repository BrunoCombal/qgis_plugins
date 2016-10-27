# -*- coding: utf-8 -*-
#from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFile, QFileInfo
#from qgis.core import *
import os, os.path

# __________
# ref.: http://pythoncentral.io/pyside-pyqt-tutorial-the-qlistwidget/
def updateBulletinList(widgetList):
	for ii in range(100):
		widgetList.addItem("Coucou {}".format(ii))

