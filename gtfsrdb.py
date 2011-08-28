#!/usr/bin/python

# gtfsrdb.py: load gtfs-realtime data to a database
# recommended to have the (static) GTFS data for the agency you are connecting
# to already loaded.

# Copyright 2011 Matt Conway

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Authors:
# Matt Conway: main code

import gtfs_realtime_pb2
from optparse import OptionParser
import time
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib2 import urlopen
from model import *

p = OptionParser()
p.add_option('-t', '--trip-updates', dest='tripUpdates', default=None, 
             help='The trip updates URL', metavar='URL')

p.add_option('-a', '--alerts', default=None, dest='alerts', 
             help='The alerts URL', metavar='URL')

p.add_option('-d', '--database', default=None, dest='dsn',
             help='Database connection string', metavar='DSN')

p.add_option('-c', '--create-tables', default=False, dest='create',
             action='store_true', help="Create tables if they aren't found")

p.add_option('-w', '--wait', default=30, type='int', metavar='SECS',
             dest='timeout', help='Time to wait between requests (in seconds)')

p.add_option('-v', '--verbose', default=False, dest='verbose', 
             action='store_true', help='Print generated SQL')

opts, args = p.parse_args()

if opts.dsn == None:
    print 'No database specified!'
    exit(1)

if opts.alerts == None and opts.tripUpdates == None:
    print 'Neither trip updates or alerts URLs were specified!'
    exit(1)

if opts.alerts == None:
    print 'Warning: no alert URL specified, proceeding without alerts'

if opts.tripUpdates == None:
    print 'Warning: no trip update URL specified, proceeding without trip updates'

# Connect to the database
engine = create_engine(opts.dsn, echo=opts.verbose)
# sessionmaker returns a class
session = sessionmaker(bind=engine)()

# Check if it has the tables
# Base from model.py
for table in Base.metadata.tables.keys():
    if not engine.has_table(table):
        if opts.create:
            print 'Creating table %s' % table
            Base.metadata.tables[table].create(engine)
        else:
            print 'Missing table %s! Use -c to create it.' % table
            exit(1)

# This is the loop
while 1:
    if opts.tripUpdates:
        fm = gtfs_realtime_pb2.FeedMessage()
        fm.ParseFromString(
            urlopen(opts.tripUpdates).read()
            )

        # Convert this a Python object, and save it to be placed into each
        # trip_update
        timestamp = datetime.datetime.utcfromtimestamp(fm.header.timestamp)

        # Check the feed version
        if fm.header.gtfs_realtime_version != u'1.0':
            print 'Warning: feed version has changed: found %s, expected 1.0' % fm.header.gtfs_realtime_version

        print 'Adding %s trip updates' % len(fm.entity)
        for entity in fm.entity:
            tu = entity.trip_update

            dbtu = TripUpdate(
                trip_id = tu.trip.trip_id,
                route_id = tu.trip.route_id,
                trip_start_time = tu.trip.start_time,
                trip_start_date = tu.trip.start_date,

                # get the schedule relationship
                # This is somewhat undocumented, but by referencing the 
                # DESCRIPTOR.enum_types_by_name, you get a dict of enum types
                # as described at http://code.google.com/apis/protocolbuffers/docs/reference/python/google.protobuf.descriptor.EnumDescriptor-class.html
                schedule_relationship = tu.trip.DESCRIPTOR.enum_types_by_name['ScheduleRelationship'].values_by_number[tu.trip.schedule_relationship].name,

                vehicle_id = tu.vehicle.id,
                vehicle_label = tu.vehicle.label,
                vehicle_license_plate = tu.vehicle.license_plate,
                timestamp = timestamp)
 
            session.add(dbtu)

            for stu in tu.stop_time_update:
                dbstu = StopTimeUpdate(
                    stop_sequence = stu.stop_sequence,
                    stop_id = stu.stop_id,
                    arrival_delay = stu.arrival.delay,
                    arrival_time = stu.arrival.time,
                    arrival_uncertainty = stu.arrival.uncertainty,
                    departure_delay = stu.departure.delay,
                    departure_time = stu.departure.time,
                    departure_uncertainty = stu.departure.uncertainty,
                    schedule_relationship = tu.trip.DESCRIPTOR.enum_types_by_name['ScheduleRelationship'].values_by_number[tu.trip.schedule_relationship].name
                    )
                session.add(dbstu)
                dbtu.StopTimeUpdates.append(dbstu)

        session.commit()

        

    # TODO: make configurable
    time.sleep(opts.timeout)
