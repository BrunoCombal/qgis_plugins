# -*- coding: utf-8 -*-
#from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFile, QFileInfo
#from qgis.core import *
import numpy
# gdal
from osgeo import gdal, ogr
from osgeo.gdalconst import *
import os, os.path, errno

# __________
# ref.: http://pythoncentral.io/pyside-pyqt-tutorial-the-qlistwidget/
def updateBulletinList(widgetList):
	for ii in range(100):
		widgetList.addItem("Coucou {}".format(ii))
# __________
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
# __________
def silentRemove(filename):
# see http://stackoverflow.com/questions/10840533/most-pythonic-way-to-delete-a-file-which-may-not-exist
	try:
		os.remove(filename)
	except OSError as e: # this would be "except OSError, e:" before Python 2.6
		if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
			raise # re-raise exception if a different error occured
# __________
def createTmpDir(conf):
	if not os.path.exists(conf["tmp_dir"]):
		os.makedirs(conf["tmp_dir"])

# __________
# Input: a shapefile, with polygon; each polygon as an id
# Input: a reference raster, will be copied to blank for burning the shapefile
def doBurnShpToRaster(shpFile, attribute, refRaster, outRaster):
	ds = gdal.Open(refRaster, GA_ReadOnly)
	cols = ds.RasterXSize
	rows = ds.RasterYSize
	projection = ds.GetProjection()
	geotransform = ds.GetGeoTransform()
	bands = 1
	datatype = GDT_Int32

	#neatline = ds.GetMetadata()['NEATLINE'] 

	#driver = ogr.GetDriverByName('Memory')
	#poly = ogr.CreateGeometryFromWkt(neatline)
	#memds = driver.CreateDataSource('tmpmemds')
	#lyr = memds.CreateLayer('neatline', geom_type=ogr.wkbPolygon)
	#feat = ogr.Feature(lyr.GetLayerDefn())
	#feat.SetGeometry(poly)
	#lyr.CreateFeature(feat)
	shpDS = ogr.Open(shpFile)
	lyr = shpDS.GetLayer()

	silentRemove(outRaster)
	driver = gdal.GetDriverByName('GTiff')
	outds = driver.Create(outRaster, cols, rows, bands, datatype, ["compress='LZW'"])
	outds.SetProjection(projection)
	outds.SetGeoTransform(geotransform)
	#gdal.RasterizeLayer(outds, [1], lyr, None, None, [1], ['ALL_TOUCHED=TRUE'])
	print "ATTRIBUTE='{}'".format(attribute)

	err = gdal.RasterizeLayer(outds, [1], lyr, options=["ATTRIBUTE={}".format(attribute)])
	if err != 0:
		print err
		print 'got non-zero result code from RasterizeLayer'
		help(gdal.RasterizeLayer)
		return 1

# __________
# Reference: a raster, pixel value=polygon id (generated with doBurnShpToRaster)
# Input: a sparse raster with 0=no detection. It must have the same resolution, projection and footprint as the detectionRaster
# Output: associative array, array[id]=count in the polygon
def doCountPerPolygonId(refRaster, detectionRaster):
	countPerId={}

	refFID = gdal.Open(refRaster, GA_ReadOnly)
	thisFID = gdal.Open(detectionRaster, GA_ReadOnly)
	ns = thisFID.RasterXSize
	nl = thisFID.RasterYSize
	countPerId = {}

	for il in range(nl):
		refLine    = numpy.ravel( refFID.GetRasterBand(1).ReadAsArray(0, il, ns, 1).astype(int) )
		dataLine   = numpy.ravel( thisFID.GetRasterBand(1).ReadAsArray(0, il, ns, 1).astype(int) )
		indexToSum = numpy.ravel( numpy.nonzero( dataLine > 0 ) ) #Returns the indices of the elements that are non-zero.

		for ii in indexToSum:
			#print 'size=', refLine.shape, dataLine.shape, indexToSum.shape
			if refLine[ii] in countPerId.keys(): # does the key already exist in countPerId?
				#print ii, len(indexToSum), refLine[ii], refLine.min(), refLine.max()
				countPerId[ refLine[ii] ] = countPerId[ refLine[ii] ] + 1
			else: # else create it
				countPerId[ refLine[ii] ] = 1
				
	return countPerId

