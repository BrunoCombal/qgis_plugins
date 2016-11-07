# -*- coding: utf-8 -*-
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFile, QFileInfo
from qgis.core import *

import os, os.path, errno
import ast

# __________
def updateConfTab(thisDlg, thisConf):

	checkMonth=[thisDlg.checkJanuary, thisDlg.checkFebruary, thisDlg.checkMarch, thisDlg.checkApril, thisDlg.checkMay,\
			thisDlg.checkJune, thisDlg.checkJuly, thisDlg.checkAugust, thisDlg.checkSeptember,\
			thisDlg.checkOctober, thisDlg.checkNovember, thisDlg.checkDecember]

	# set to 0 first
	for icheck in checkMonth:
		icheck.setEnabled(True)
		icheck.setChecked(False)

	# set to 1 those selected in the configuration file
	for imonth in thisConf['season']:
		checkMonth[ imonth-1 ].setChecked(True)

