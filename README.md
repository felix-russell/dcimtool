Python Script for migrating data out of the OpenDCIM database and into Netbox.
========

Supported Data Types:
* Tenants
* Sites
* Rack Groups
* Racks
* Manufacturers
* Device Types
* Devices
* Child Devices
* Device Bays

Requirements:
* Python 2,3 
* python packages: 
requests, django-utils, mysql-connector-python-rf, pycurl, slugify, dnspython

Instructions:
* OpenDCIM:
1. Create a custom device attribute named migrate_color with a hex code default value (eg. 00ff00)
2. Create a custom device attribute named default_face with default value type binary (eg. 0 for front, 0 for rear facing)
3. Include the string 'sled' in the name of all child device templates. (eg. Dell c6320 sled)
4. Elimiate duplicate asset tags, names, or overlapped devices in the openDCIM database, this will cause the script to fail.
5. Do not attempt to use 'storage rooms' in OpenDCIM, create a tall rack in the Datacenter of your choice and slot the devices in 'storage' there temporarily for migration

* Netbox
1. Install netbox according the instructions found on the readthedocs wiki.
2. Generate netbox API token for a superuser account a superuser account.

* Script variables
1. Populate variables dbHost, dbUser, dbPasswd, dbName, netboxBaseURL, netboxToken, and netboxUser.
2. Set debug verbosity levels in the booleans
3. Run script
4. Read the dump files created for the script for debugging


Author
----
(c)2017 University of Washington, Institute for Health Metrics and Evaluation
 - Felix Russell (felix-russell@github.com)

Tested/supported versions
----
* OpenDCIM 4.1
* Netbox 2.1d