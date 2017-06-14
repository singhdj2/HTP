#!/usr/bin/python
#
# Program: create_uas_metadata_file
#
# Version: 0.4 June 2,2016  Improved accuracy of interpolation
#
# Version: 0.3 June 1,2016  First fully working version
#
# Version: 0.2 May 27,2016
#
# Version: 0.1 May 23,2016
#
# Creates CSV file containing image metadata to be imported into the uas_images table in the wheatgenetics database.
#
# Command Line Inputs:
#
#
# '-d' or '--dir':      'Beocat directory path to UAV image files', default='/homes/mlucas/uas_incoming/'
# '-l' or '--log':    'Flight log path
# '-t' or '--type':     'Image file type, e.g. CR2, JPG'
# '-o' or '--out':      'Output file path and filename'
#
#

__author__ = 'mlucas'

import subprocess
import csv
import time
import math
import sys
import argparse
import hashlib
import exifread
import utm
import datetime
import pytz
from pytz import timezone
from tzlocal import get_localzone
import collections
import bisect



secsInWeek = 604800
secsInDay = 86400
gpsEpoch = (1980, 1, 6, 0, 0, 0)  # (year, month, day, hh, mm, ss)
null_date = '0000/00/00'
null_time = '00:00:00'
epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=pytz.UTC)

bufsize = 1  # Use line buffering, i.e. output every line to the file.

# Declare Tags for image EXIF data
gpsAltTag       = 'GPS GPSAltitude'
gpsAltRefTag    = 'GPS GPSAltitudeRef'
gpsLatTag       = 'GPS GPSLatitude'
gpsLatRefTag    = 'GPS GPSLatitudeRef'
gpsLongTag      = 'GPS GPSLongitude'
gpsLongRefTag   = 'GPS GPSLongitudeRef'
TimeTag         = 'Time Codes'
DateTag         = 'EXIF DateTimeDigitized'

def get_image_file_list(fuasPath, fimageType):
    # Return a list of the names and sample date & time for all image files.

    imagefilelist = []

    # Get list of files in uas staging directory

    print("Fetching list of image files...")

    filestocheck = subprocess.check_output(['ls', '-1', fuasPath], universal_newlines=True)

    afile = ''
    filelist = []

    for char in filestocheck:
        if char != '\n':
            afile += char
        else:
            filelist.append(afile)
            afile = ''

            # Get the subset of files that are the image files

    for ff in filelist:
        startPos = len(ff) - 3
        endPos = len(ff)
        isimagefile = (ff != '' and ff[startPos:endPos] == fimageType)
        if isimagefile:
            imagefilelist.append(ff)
    return imagefilelist

def interpolate_time(fflightLog):
    gpsEventDict=collections.OrderedDict()  # stores position,altitude,video status, interpolation indicator with time as key
    gpsEventList=[]
    rowCount=0
    timestamp=0
    seedTime=0
    newTime=0
    prevTime=0
    nextTime=0
    timeDelta=0
    takingVideo='0'
    prevLat=0.0
    nextLat=0.0
    prevLong=0.0
    nextLong=0.0
    prevAlt=0.0
    nextAlt=0.0
    latitude=0.0
    longitude=0.0
    altitude=0.0
    with open(fflightLog, 'rU') as logfile:
        log = logfile.readlines()
        for row in log:
            rowCount += 1
            if rowCount > 1:
                rowFields = row.split(',')
                latitude=float(rowFields[0])
                longitude=float(rowFields[1])
                utmPosition=utm.from_latlon(latitude,longitude)
                utmPositionX=utmPosition[0]
                utmPositionY=utmPosition[1]
                utmLatZone=utmPosition[2]
                utmLongZone=utmPosition[3]
                altitude =float(rowFields[2])*0.3048
                lYear=rowFields[11][0:4]
                lMonth=rowFields[11][5:7]
                lDay=rowFields[11][8:10]
                lhours=rowFields[11][11:13]
                lminutes = rowFields[11][14:16]
                lsecs = rowFields[11][17:19]
                lmsecs = rowFields[11][20:]
                lDate=lYear+'/'+lMonth+'/'+lDay
                lTime=lhours+':'+lminutes+':'+lsecs+'.'+lmsecs
                #$timeInSecs=float(rowFields[43])/1000
                takingVideo=rowFields[37]
                timestamp = int(rowFields[43])
                interpolated=False
                nextTime=timestamp
                nextLat=latitude
                nextLong=longitude
                nextAlt=altitude
                #if takingVideo=='1':
                #    gpsEventList=[lDate,lTime,latitude,longitude,altitude,takingVideo,interpolated,timestamp,utmPositionX,utmPositionY,utmLatZone,utmLongZone]
                #    gpsEventDict[timestamp] = gpsEventList
                if rowCount >=2 and takingVideo=='1':
                    if seedTime == 0:
                        seedTime = round((timestamp + 5) / 1000.0, 2) * 1000
                        newTime = seedTime
                    timeDelta = nextTime - prevTime
                    latDelta=nextLat-prevLat
                    longDelta=nextLong-prevLong
                    altDelta=nextAlt-prevAlt
                    interpolated = False
                    # new* are variables used to store interpolated values between the endpoints of the calculated
                    # intervals of time, latitude, longitude and altitude.
                    newTimeStr = datetime.datetime.utcfromtimestamp(newTime / 1000.0).strftime('%Y/%m/%d %H:%M:%S.%f')
                    newDateStr = newTimeStr.split(' ')[0]
                    newTimeStr = newTimeStr.split(' ')[1]
                    newLat = prevLat
                    newLong = prevLong
                    newUtmPosition = utm.from_latlon(newLat, newLong)
                    newUtmPositionX = newUtmPosition[0]
                    newUtmPositionY = newUtmPosition[1]
                    newUtmLatZone = newUtmPosition[2]
                    newUtmLongZone = newUtmPosition[3]
                    newAlt = prevAlt
                    # Normal sampling interval is 100ms. The interpolated sampling interval is 10 ms.
                    # If the difference between the two times of interest is > 20 ms perform interpolation
                    lastTime=prevTime
                    if abs(timeDelta) > 10:
                        interpolated=True
                        while newTime < nextTime:
                            timeFraction= (newTime-lastTime)/timeDelta
                            if latDelta > 0.0:
                                newLat += abs(latDelta) * timeFraction
                            elif latDelta < 0.0:
                                newLat -= abs(latDelta) * timeFraction
                            if longDelta > 0.0:
                                newLong += abs(longDelta) * timeFraction
                            elif longDelta < 0.0:
                                newLong -= abs(longDelta) * timeFraction
                            if altDelta > 0.0:
                                newAlt += abs(altDelta) * timeFraction
                            elif altDelta < 0.0:
                                    newAlt -= abs(altDelta) * timeFraction
                            newTimeStr = datetime.datetime.utcfromtimestamp(newTime / 1000.0).strftime(
                                '%Y/%m/%d %H:%M:%S.%f')
                            newDateStr = newTimeStr.split(' ')[0]
                            newTimeStr = newTimeStr.split(' ')[1]
                            gpsEventList = [newDateStr, newTimeStr, newLat, newLong, newAlt, takingVideo, interpolated,
                                            newTime, newUtmPositionX, newUtmPositionY, newUtmLatZone, newUtmLongZone]
                            gpsEventDict[newTime] = gpsEventList
                            lastTime=newTime
                            newTime += 10

                            #time.sleep(0.1)
                    else:
                        newTime+=0
                        #print 'No Data Stored'
            prevTime = timestamp
            prevLat = latitude
            prevLong = longitude
            prevAlt = altitude
            #print gpsEventList
    return gpsEventDict

def get_image_utm_position(fgpsLatitude, fgpsLongitude):
    futmPosition = utm.from_latlon(fgpsLatitude, fgpsLongitude)

    return futmPosition

def hashfilelist(afile, blocksize=65536):
    hasher = hashlib.md5()
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.hexdigest()


def calculate_checksum(ffilename):
    checksum = hashfilelist(open(ffilename, 'rb'))
    return checksum

def get_image_exif_data(ffilename):
    tags = exifread.process_file(image)
    fcam_position_x     = None
    fcam_position_y     = None
    fcam_position_z     = None
    fcam_latitude       = None
    fcam_longitude      = None
    fcam_sample_date    = null_date
    fcam_sample_time    = null_time
    fcam_lat_zone       = None
    fcam_long_zone      = None
    fcam_altitude_ref   = None
    fframe_number_str   = None
    fframe_number_dec = None
    try:

    # Get Camera GPS Altitude
        if gpsAltTag in tags:
            altStr          = str(tags[gpsAltTag])
            if '/' in altStr:
                altNum,altDenom = altStr.split('/')
                fcam_position_z  = str(float(altNum)/float(altDenom))
            else:
                fcam_position_z = altStr
        else:
            fcam_position_z = '0'


    #    Get Camera GPS Altitude reference MSL - Mean Sea Level BMSL = Below Mean Sea Level

        if gpsAltRefTag in tags:
            altRefStr = str(tags[gpsAltRefTag])
            if altRefStr == '0':
                fcam_altitude_ref='AMSL'
            else:
                fcam_altitude_ref='BMSL'
        else:
            fcam_altitude_ref='Not Available'


    # Get Camera GPS Latitude and Longitude Data
        latRefStr       = str(tags[gpsLatRefTag])
        latStrLen       = len(str(tags[gpsLatTag]))-1
        latStr          = str(tags[gpsLatTag])[1:latStrLen]
        lat,latMins,latSecs = latStr.split(', ')
        if '/' in latSecs:
            latSecsNum,latSecsDenom = latSecs.split('/')
            latSecsDec = float(latSecsNum)/float(latSecsDenom)
        else:
            latSecsDec=float(latSecs)

        if '/' in latMins:
            latMinsNum, latMinsDenom = latMins.split('/')
            latMinsDec = float(latMinsNum) / float(latMinsDenom)
        else:
            latMinsDec = float(latMins)

        if latRefStr == "S":
            fcam_latitude = (float(lat)+ latMinsDec/60 + latSecsDec/3600) * (-1)
        elif latRefStr == "N":
            fcam_latitude = (float(lat)+ latMinsDec/60 + latSecsDec/3600)


        longRefStr      = str(tags[gpsLongRefTag])
        lonStrLen       = len(str(tags[gpsLongTag]))-1
        lonStr          = str(tags[gpsLongTag])[1:lonStrLen]
        lon,lonMins,lonSecs = lonStr.split(', ')
        if '/' in lonSecs:
            lonSecsNum,lonSecsDenom = lonSecs.split('/')
            lonSecsDec = float(lonSecsNum)/float(lonSecsDenom)
        else:
            lonSecsDec=float(lonSecs)

        if '/' in lonMins:
            lonMinsNum, lonMinsDenom = lonMins.split('/')
            lonMinsDec = float(lonMinsNum) / float(lonMinsDenom)
        else:
            lonMinsDec = float(lonMins)

        if longRefStr == "W":
            fcam_longitude = (float(lon)+ lonMinsDec/60 + lonSecsDec/3600) * (-1)
        elif longRefStr == "E":
            fcam_longitude = (float(lon)+ lonMinsDec/60 + lonSecsDec/3600)

    # Get Camera UTM Position
        camUtmPosition  = get_image_utm_position(fcam_latitude, fcam_longitude)
        fcam_position_x = camUtmPosition[0]
        fcam_position_y = camUtmPosition[1]

    # Get Camera Latitude and Longitude Zone

        fcam_lat_zone   = camUtmPosition[2]
        fcam_long_zone  = camUtmPosition[3]


    # Get Camera Frame Number
        timecodes=str(tags['Image Tag 0xC763'])
        tc1,tc2,tc3,tc4,tc5,tc6,tc7,tc8=timecodes.split(',')
        fframeNumber=str(hex(int(tc1[1:])))[2:]


    # Get Camera Image Date and Time

        dateStr=str(tags[DateTag])

        localTz=get_localzone()
        fcamTime = datetime.datetime.strptime(dateStr, "%Y:%m:%d %H:%M:%S")
        local_dt = localTz.localize(fcamTime, is_dst=None)
        utc_dt=local_dt.astimezone(pytz.utc)
        fcamTimeUTCInSecs = int(round(((utc_dt - epoch).total_seconds() + (int(fframeNumber) * (1.0 / 24.0)))*1000.0))
        #fcamTimeUTCInSecs = (((utc_dt - epoch).total_seconds() + (int(fframeNumber) * (1.0 / 24.0))) * 1000.0)
        #print "%3f" % fcamTimeUTCInSecs,ffilename

    except Exception,e:
        print '*** Error*** Unable to process image file EXIF data for '
        print '*** Error Code:',e
        print '*** Null EXIF-based column values will be generated for',ffilename
    return fcamTimeUTCInSecs,fframeNumber



def init_metadata_record():
    record_id=None
    imagefilename=None
    uas_position_x=None
    uas_position_y=None
    uas_position_z=None
    uas_latitude=None
    uas_longitude=None
    uas_sample_date_utc=null_date
    uas_sample_time_utc=null_time
    uas_latzone=None
    uas_longzone=None
    uas_altitude_ref='AGL'
    cam_position_x=None
    cam_position_y=None
    cam_position_z=None
    cam_latitude=None
    cam_longitude=None
    cam_sample_date_utc=null_date
    cam_sample_time_utc=null_time
    cam_lat_zone=None
    cam_long_zone=None
    cam_altitude_ref=None
    f_checksum=None
    notes=''
    blankrow = [record_id, imagefilename, flightId, sensor_id, uas_position_x, uas_position_y,
                uas_position_z, uas_latitude, uas_longitude, uas_sample_date_utc, uas_sample_time_utc,
                uas_latzone, uas_longzone, uas_altitude_ref, cam_position_x, cam_position_y, cam_position_z,
                cam_latitude, cam_longitude, cam_sample_date_utc, cam_sample_time_utc, cam_lat_zone,
                cam_long_zone, cam_altitude_ref, f_checksum, notes]
    return blankrow


# Get command line input.

cmdline = argparse.ArgumentParser()

cmdline.add_argument('-d', '--dir', help='Beocat directory path to HTP imagefiles',
                     default='/homes/mlucas/uas_incoming/')

cmdline.add_argument('-l', '--log', help='Flight Log File name')

cmdline.add_argument('-t', '--type', help='Image file type extension, e.g. CR2, JPG',
                     default='CR2')


args = cmdline.parse_args()

uasPath = args.dir
flightLog = args.log
imageType = args.type

startPos=uasPath.find('DJI')
sensor_id=uasPath[startPos:startPos+10]
print ' '
print "Camera ID: ",sensor_id

record_id = None
notes = ''
metadatalist = []

gpsEvents =interpolate_time(flightLog)

# Get the list of image files available for the flight/

imagefiles = get_image_file_list(uasPath,imageType)
if len(imagefiles)==0:
    print "There were no image files found in ",uasPath
    print "Exiting"
    sys.exit(10)

if len(gpsEvents)==0:
    print "There were no gps events found in", flightLog
    print

fltStartString=datetime.datetime.utcfromtimestamp(min(gpsEvents.keys())/1000.0)
fltEndString=datetime.datetime.utcfromtimestamp(max(gpsEvents.keys())/1000.0)
fltStart=time.gmtime(min(gpsEvents.keys())/1000.0)
fltEnd=time.gmtime(max(gpsEvents.keys())/1000.0)
print ''
print 'Flight Start: ',fltStartString
print 'Flight End: ',fltEndString

flightId='uas_'+ str(fltStart[0])+str(fltStart[1]).zfill(2)+str(fltStart[2]).zfill(2)+ '_' + \
         str(fltStart[3]).zfill(2) + str(fltStart[4]).zfill(2) + str(fltStart[5]).zfill(2) + '_' + \
         str(fltEnd[0]) + str(fltEnd[1]).zfill(2) + str(fltEnd[2]).zfill(2) + '_' + \
         str(fltEnd[3]).zfill(2) + str(fltEnd[4]).zfill(2) + str(fltEnd[5]).zfill(2)
print ''
print 'Flight ID:', flightId

#
# Define UAS Metadata Output File Path
#
uasMetadataFile= uasPath + flightId + '_metadata.csv'
print ''
print 'UAS Metadata Output File: ',uasMetadataFile

#
# Switch image folders to JPEG folder
uasPathJpg=uasPath[0:(len(uasPath)-1)] +'_JPEG' +'/'

camIndex = 0
try:
    for f in imagefiles:
        metadata_record=init_metadata_record()
        f_jpg = f.split('.')[0] + '.jpg'
        filename_jpg = uasPathJpg + f_jpg
        filename_dng = uasPath + f
        imagefilename = f_jpg
        metadata_record[24]=calculate_checksum(filename_jpg)
        metadata_record[0]=record_id
        metadata_record[1]=imagefilename
        metadata_record[2]=flightId
        metadata_record[3]=sensor_id
    #
    #Get Date, Time and Frame Number From Image File EXIF metadata
    #
        with open(filename_dng,'rb') as image:
            print "Processing ",filename_dng
            cam_time_in_seconds,cam_frame_number=get_image_exif_data(filename_dng)
        image.close()
    #
    # Interpolate Longitude,Latitude and Altitude of image
    # Need to convert date/time/frame to timestamp
    #
        logTimeIndex=bisect.bisect_right(sorted(gpsEvents.keys()),cam_time_in_seconds)
        tDelta=(gpsEvents.keys()[logTimeIndex]-cam_time_in_seconds)
        tDeltaPrev=(gpsEvents.keys()[logTimeIndex-1]-cam_time_in_seconds)
        if (tDelta <= tDeltaPrev):
            gpsEventsKey= gpsEvents.keys()[logTimeIndex]
        else:
            gpsEventsKey = gpsEvents.keys()[logTimeIndex-1]
        gpsEvents[gpsEventsKey].extend((logTimeIndex,cam_time_in_seconds, abs(gpsEventsKey - cam_time_in_seconds),f_jpg))
        print ''
        uas_position_x=gpsEvents[gpsEventsKey][8]
        uas_position_y=gpsEvents[gpsEventsKey][9]
        uas_position_z=gpsEvents[gpsEventsKey][4]
        uas_latitude=gpsEvents[gpsEventsKey][2]
        uas_longitude=gpsEvents[gpsEventsKey][3]
        uas_sample_date_utc=gpsEvents[gpsEventsKey][0]
        uas_sample_time_utc=gpsEvents[gpsEventsKey][1]
        uas_latzone=gpsEvents[gpsEventsKey][10]
        uas_longzone=gpsEvents[gpsEventsKey][11]


        metadata_record[4] = uas_position_x
        metadata_record[5] = uas_position_y
        metadata_record[6] = uas_position_z
        metadata_record[7] = uas_latitude
        metadata_record[8] = uas_longitude
        metadata_record[9] = uas_sample_date_utc
        metadata_record[10] = uas_sample_time_utc
        metadata_record[11] = uas_latzone
        metadata_record[12] = uas_longzone

        #time.sleep(0.01)
        metadatalist.append(metadata_record)
        camIndex += 1
except Exception, e:
    print '*** Error*** Unable to process image file.'
    print '*** Error Code:', e
    print '*** Exiting...'

#i=0
#for key in sorted(gpsEvents.iterkeys()):
#    print('*',i,key,gpsEvents[key])
#    i+=1
#for r in metadatalist:
#    print r

with open(uasMetadataFile, 'wb') as csvfile:
    header = csv.writer(csvfile)
    header.writerow(
        ['record_id', 'image_file_name','flight_id', 'sensor_id', 'uas_position_x',
         'uas_position_y', 'uas_position_z', 'uas_latitude','uas_longitude','uas_sampling_date_utc','uas_sampling_time_utc',
         'uas_lat_zone', 'uas_long_zone','uas_altitude_reference','cam_position_x','cam_position_y', 'cam_position_z',
         'cam_latitude','cam_longitude','cam_sampling_date_utc','cam_sampling_time_utc','cam_lat_zone', 'cam_long_zone',
         'cam_altitude_reference', 'md5sum', 'notes'])
csvfile.close()

with open(uasMetadataFile, 'ab') as csvfile:
    print 'Generating metadata file', uasMetadataFile
    for lineitem in metadatalist:
        fileline = csv.writer(csvfile)
        fileline.writerow(
            [lineitem[0], lineitem[1], lineitem[2], lineitem[3], lineitem[4], lineitem[5], lineitem[6], lineitem[7],
             lineitem[8], lineitem[9], lineitem[10], lineitem[11], lineitem[12], lineitem[13], lineitem[14],
             lineitem[15],lineitem[16],lineitem[17],lineitem[18],lineitem[19],lineitem[20],lineitem[21],lineitem[22],
             lineitem[23],lineitem[24]])
csvfile.close()

# Exit the program gracefully

print ('Processing Completed. Exiting...')
sys.exit()
