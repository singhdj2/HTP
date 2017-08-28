#!/usr/bin/python
#
# Program: convert_experiment_coordinate_syste,

# Version: 0.1 August 24,2017
#
# This program will query a set of experiments,convert the coordinate system to long/lat and save the results to a file.
#

from math import sqrt
import sys
import mysql.connector
from mysql.connector import errorcode
import config
import os
import utm
import csv
from shapely.geometry import Point, LineString, Polygon

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


exptList=[]

experimentPath= '/Users/mlucas/Desktop/HTP_Database_Updates/experimentLonLat.csv'


# Query the database for the experiment records

cursor, cnx = open_db_connection(config)
exptQuery=("SELECT * FROM experiment")

try:
    cursor.execute(exptQuery, )
    if cursor.rowcount != 0:
        for row in cursor:
            recordId=str(int(row[0]))
            experimentId=row[1].replace("_","-")
            experimentId=experimentId.strip(' \t\n\r')
            location=row[2]
            environment=row[3]
            plantingDate=row[4]
            harvestDate=row[5]
            c1_1_x = row[6]
            c1_1_y = row[7]
            c1_2_x = row[9]
            c1_2_y = row[10]
            c2_1_x = row[12]
            c2_1_y = row[13]
            c2_2_x = row[15]
            c2_2_y = row[16]
            lat_zone=row[18]
            long_zone=row[19]
            notes=row[20]

            c1_1_longitude=None
            c1_1_latitude=None
            c1_2_longitude = None
            c1_2_latitude = None
            c2_1_longitude = None
            c2_1_latitude = None
            c2_2_longitude = None
            c2_2_latitude = None

            if (c1_1_x !=0 and c1_1_x != None) and (long_zone != None and lat_zone !=None):
                c1_1_latLonPosition=utm.to_latlon(c1_1_x,c1_1_y,int(long_zone),lat_zone)
                c1_1_latitude=c1_1_latLonPosition[0]
                c1_1_longitude=c1_1_latLonPosition[1]
                c1_1_latCoord=str(c1_1_latLonPosition[0])
                c1_1_lonCoord=str(c1_1_latLonPosition[1])
                c1_1_back_convert=utm.from_latlon(c1_1_latLonPosition[0],c1_1_latLonPosition[1])
                c1_1_back_convert_error_cm=(sqrt((c1_1_back_convert[0]-c1_1_x)**2 +(c1_1_back_convert[1]-c1_1_y)**2 ))*100.0

            if (c1_2_x != 0 and c1_2_x != None) and (long_zone != None and lat_zone != None):
                c1_2_latLonPosition = utm.to_latlon(c1_2_x, c1_2_y, int(long_zone), lat_zone)
                c1_2_latitude = c1_2_latLonPosition[0]
                c1_2_longitude = c1_2_latLonPosition[1]
                c1_2_latCoord=str(c1_2_latLonPosition[0])
                c1_2_lonCoord=str(c1_2_latLonPosition[1])
                c1_2_back_convert=utm.from_latlon(c1_2_latLonPosition[0],c1_2_latLonPosition[1])
                c1_2_back_convert_error_cm=(sqrt((c1_2_back_convert[0]-c1_2_x)**2 +(c1_2_back_convert[1]-c1_2_y)**2 ))*100.0

            if (c2_1_x != 0 and c2_1_x != None) and (long_zone != None and lat_zone != None):
                c2_1_latLonPosition = utm.to_latlon(c2_1_x, c2_1_y, int(long_zone), lat_zone)
                c2_1_latitude = c2_1_latLonPosition[0]
                c2_1_longitude = c2_1_latLonPosition[1]
                c2_1_latCoord = str(c2_1_latLonPosition[0])
                c2_1_lonCoord = str(c2_1_latLonPosition[1])
                c2_1_back_convert = utm.from_latlon(c2_1_latLonPosition[0], c2_1_latLonPosition[1])
                c2_1_back_convert_error_cm = (sqrt((c2_1_back_convert[0] - c2_1_x) ** 2 + (c2_1_back_convert[1] - c2_1_y) ** 2)) * 100.0

            if (c2_2_x != 0 and c2_2_x != None) and (long_zone != None and lat_zone != None):
                c2_2_latLonPosition = utm.to_latlon(c2_2_x, c2_2_y, int(long_zone), lat_zone)
                c2_2_latitude = c2_2_latLonPosition[0]
                c2_2_longitude = c2_2_latLonPosition[1]
                c2_2_latCoord = str(c2_2_latLonPosition[0])
                c2_2_lonCoord = str(c2_2_latLonPosition[1])
                c2_2_back_convert = utm.from_latlon(c2_2_latLonPosition[0], c2_2_latLonPosition[1])
                c2_2_back_convert_error_cm = (sqrt((c2_2_back_convert[0] - c2_2_x) ** 2 + (c2_2_back_convert[1] - c2_2_y) ** 2)) * 100.0

            if c1_1_latitude != None:
                exptPolygon=Polygon([(c1_1_longitude,c1_1_latitude),(c1_2_longitude,c1_2_latitude),(c2_1_longitude,c2_1_latitude),(c2_2_longitude,c2_2_latitude),(c1_1_longitude,c1_1_latitude)])
                exptListItem = [recordId, experimentId, location, environment, plantingDate, harvestDate, exptPolygon.wkt]
                print recordId, experimentId, c1_1_x, c1_1_y, c1_1_lonCoord, c1_1_latCoord, long_zone, lat_zone
                print "Original UTM c1_1_x                      = " + str(c1_1_x)
                print "Origianl UTM c1_1_y                      = " + str(c1_1_y)
                print "Back Converted UTM x                     = " + str(c1_1_back_convert[0])
                print "Back Converted UTM y                     = " + str(c1_1_back_convert[1])
                print "UTM x Back Conversion Delta              = " + str((c1_1_back_convert[0] - c1_1_x) * 100.0) + " centimeters"
                print "UTM y Back Conversion Delta              = " + str((c1_1_back_convert[1] - c1_1_y) * 100.0) + " centimeters"
                print "UTM Pythagorean Back Conversion Error    = " + str(c1_1_back_convert_error_cm) + " centimeters"
                print
            else:
                exptListItem = [recordId, experimentId, location, environment, plantingDate, harvestDate, None]

            exptList.append(exptListItem)



except:
    print 'Unexpected error during database query:', sys.exc_info()[0]
    sys.exit()

print('Committing changes and closing connection to database table: experiment ')
commit_and_close_db_connection(cursor, cnx)


# Write out the experiment file with long/lat coords

with open(experimentPath,'wb') as csvFile:
    print 'Writing Experiment Long/Lat File'
    header=csv.writer(csvFile)
    header.writerow(['record_id', 'experiment_id', 'location', 'environment', 'planting_date', 'harvest_date', 'expt_polygon'])
csvFile.close()

with open(experimentPath,'ab') as csvFile:
    for row in exptList:
        fileline = csv.writer(csvFile,quoting=csv.QUOTE_ALL,lineterminator = ',\n')
        fileline.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6]])
    # Kludge to get rid of blank last line in the file which causes an empty row to be loaded into the database
    # when using LOAD DATA INFILE procedure!!
    csvFile.seek(-2, os.SEEK_END)
    csvFile.truncate()
csvFile.close()
sys.exit()


