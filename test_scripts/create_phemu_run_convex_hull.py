#!/usr/bin/python
#
# Program: create_phemu_run_convex_hill

# Version: 0.1 August 28,2017
#
# This program will query a set of phemu_images records and phemu_htp records,and generate a convex_hull
#

from math import sqrt
import sys
import mysql.connector
from mysql.connector import errorcode
import test_config
import os
from pyproj import Proj, transform
import csv
from shapely.wkt import dumps
from shapely.geometry import Point, LineString, Polygon,MultiPoint
import pytz
from tzlocal import get_localzone
from timezonefinder import TimezoneFinder
import datetime


def convert_polygon_coord_system(plt):
    LonLatCoordString = 'POLYGON(('
    coordString=plt[9:-2]
    coords=coordString.split(',')
    for pos in coords:
        coordPair=str(pos).split(' ')
        x=float(coordPair[0])
        y=float(coordPair[1])
        latLonPosition=utm.to_latlon(x,y,longZone,latZone)
        latCoord=str(latLonPosition[0])
        lonCoord=str(latLonPosition[1])
        LonLatCoordString+=lonCoord + ' ' + latCoord + ','
    LonLatPlt=LonLatCoordString[0:-1] + '))'
    return LonLatPlt


def open_db_connection(config):

    # Connect to the HTP database
        try:
            cnx = mysql.connector.connect(user=config.USER, password=config.PASSWORD,
                                          host=config.HOST, port=config.PORT,
                                          database=config.DATABASE)
            print('Connecting to Database: ' + cnx.database)

        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
                sys.exit()
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
                sys.exit()
            else:
                print(err)
        else:
            print('Connected to MySQL database:' + cnx.database)
            cursor = cnx.cursor(buffered=True)
        return cursor,cnx


def commit_and_close_db_connection(cursor,cnx):

    # Commit changes and close cursor and connection

    try:
        cnx.commit()
        cursor.close()
        cnx.close()

    except Exception as e:
            print('There was a problem committing database changes or closing a database connection.')
            print('Error Code: ' + e)

    return


runList=[]
utmProj = Proj(init='epsg:32614') # Data is only from Kansas
WGS84Proj = Proj(init='epsg:4326')
phemuRunPath= '/Users/mlucas/Desktop/HTP_Database_Updates/phemu_run/phemu_run_update_latlong.csv'


# Query the database for the experiment records

cursorA, cnxA = open_db_connection(test_config)
cursorB, cnxB = open_db_connection(test_config)
cursorC, cnxC = open_db_connection(test_config)

get_phemu_run_ids = "SELECT * from phemu_run"
get_htp_run_coords = "SELECT ST_X(position),ST_Y(position) from phemu_htp where run_id like %s"
get_image_run_coords = "SELECT ST_X(position),ST_Y(position) from phemu_images where run_id like %s"

print ''
try:
    cursorA.execute(get_phemu_run_ids, )
    if cursorA.rowcount != 0:
        for rowA in cursorA:
            recordId=str(int(rowA[0]))
            runId=rowA[1]
            startDate=rowA[2]
            startTime=rowA[3]
            startDateStr=str(rowA[2])
            startTimeStr=str(rowA[3])
            endDate=rowA[4]
            endTime=rowA[5]
            runFolder=rowA[6]
            notes=rowA[14]
            surveyed=rowA[15]

            pointList = []
            cursorB.execute(get_htp_run_coords,(runId, ))
            for rowB in cursorB:
                longitude_h, latitude_h = transform(utmProj, WGS84Proj, rowB[0], rowB[1])
                pointList.append((longitude_h,latitude_h))

            if cursorB.rowcount ==0:
                htpPolygon=None
                observationCount=0
            else:
                htpPolygon = dumps((MultiPoint(pointList)).convex_hull)
                observationCount=cursorB.rowcount

            startYear, startMonth, startDay = startDateStr.split("-")
            startHour, startMinute, startSecond = startTimeStr.split(':')
            tf = TimezoneFinder()
            tzone = tf.timezone_at(lng=longitude_h, lat=latitude_h)
            tz=pytz.timezone(tzone)
            utc_dt = datetime.datetime(int(startYear), int(startMonth), int(startDay), int(startHour), int(startMinute),
                                       int(startSecond), tzinfo=pytz.utc)
            dt = utc_dt.astimezone(tz)

            localDate=dt.date()
            localTime=dt.time()

            runListItem = [recordId, runId,startDate,startTime,endDate,endTime,localDate,localTime,runFolder,notes,surveyed, htpPolygon,observationCount]
            print "phemu_htp   ",cursorB.rowcount,runListItem

            pointList = []
            cursorC.execute(get_image_run_coords, (runId,))
            for rowC in cursorC:
                longitude_i, latitude_i = transform(utmProj, WGS84Proj, rowC[0], rowC[1])
                pointList.append((longitude_i, latitude_i))

            if cursorC.rowcount == 0:
                imagePolygon=None
                imageCount=0
            else:
                imagePolygon = dumps((MultiPoint(pointList)).convex_hull)
                imageCount=cursorC.rowcount


            runListItem.extend([imagePolygon,imageCount])
            print "phemu_images",cursorC.rowcount,runListItem
            runList.append(runListItem)
            print ''

except:
    print 'Unexpected error during database query:', sys.exc_info()[0]
    cursorA.close()
    cursorB.close()
    cursorC.close()
    cnxA.close
    cnxB.close
    cnxC.close
    sys.exit()

print('Committing changes and closing connection to database table: phemu_run ')
commit_and_close_db_connection(cursorA, cnxA)
commit_and_close_db_connection(cursorB, cnxB)
commit_and_close_db_connection(cursorC, cnxC)
# Write out the experiment file with long/lat coords

with open(phemuRunPath,'wb') as csvFile:
    print 'Writing phemu_run polygon File'
    header=csv.writer(csvFile)
    header.writerow(['record_id', 'run_id','start_date_utc','start_time_utc','end_date_utc','end_time_utc','start_date_local','start_time_local','run_folder_name','notes','surveyed', 'htp_polygon','observation_count', 'image_polygon','image_count'])
csvFile.close()

with open(phemuRunPath,'ab') as csvFile:
    for row in runList:
        fileline = csv.writer(csvFile,quoting=csv.QUOTE_ALL,lineterminator = ',\n')
        fileline.writerow([row[0], row[1], row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14]])
    # Kludge to get rid of blank last line in the file which causes an empty row to be loaded into the database
    # when using LOAD DATA INFILE procedure!!
    csvFile.seek(-2, os.SEEK_END)
    csvFile.truncate()
csvFile.close()
sys.exit()


