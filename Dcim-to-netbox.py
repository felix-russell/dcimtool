import sys
import json
import collections
from django.utils.http import urlquote
import requests
from slugify import slugify
import mysql.connector
import dns.resolver
import dns.zone

### OpenDCIM Database Connection Settings
dbHost = "openDcimDbHost.example.com"
dbUser = "openDcimDbUser"
dbPasswd = "openDcimDbPassword"
dbName = "OpenDcimDbName"

### Netbox API connection Settings ###
baseNetboxUrl = "http://netbox-app-p01.example.com:80/"
netboxToken = 'NetboxRootUserApiToken'
netboxUser = "NetboxAdminUser"

### Mapfile where the queries and the API output locations variables are set ###
queryMapFile = 'QueryMap.json'

### booleans for enabling various debug data output ###
ingestDebugFlag = True
dcimOutputEnableFlag = True
outputDebugFlag = True
outputResponseFlag = True
reQueryResponseFlag = False

### Locaion of output log dumps. Set to text file because output verbosity can overwhelm terminal buffers ###
debugOutputFile = open("DUMP.txt","w+")
sys.stdout = open('stdoutdump.txt', 'w+')

### Initialization of variables for data retrieval and requery ###
commonHeaders = {
    'Authorization': 'Token ' + netboxToken,
    'Accept': 'application/json; indent=4',
}
dcimRequeryTypes = ["device-roles/", "manufacturers/", "device-types/","sites/", "racks/", "rack-groups/", "devices/", "inventory-items/", "device-bays/",]
tenancyRequeryTypes = ["tenants/"]
netboxLoginURL = baseNetboxUrl + "login/"

postCountDict = collections.OrderedDict()

class apiEngine:
    def __init__(self, sType, sSubType):
        self.netboxAPIurl = baseNetboxUrl +  "api/" + sType + sSubType
        self.client = requests.session()
        self.client.get(netboxLoginURL)
        self.csrftoken = self.client.cookies['csrftoken']
        self.retrieveHeaders = commonHeaders
        self.retrieveHeaders.update({'X-CSRFToken': self.csrftoken})
        self.submitHeaders = self.retrieveHeaders
        self.submitHeaders.update({'Content-Type': 'application/json'})

    def netboxSubmit(self, sObject):
        if outputDebugFlag:
            print("? ATTEMPTING TO POST \'" + sObject + "\'")
        response = self.client.post(self.netboxAPIurl, data=sObject, headers=self.submitHeaders)
        if outputResponseFlag:
            print("! SUCCESSFUL POST OF THE FOLLOWING: \'" + response.text + "\'")
            debugOutputFile.write(str(response.text)) 

    def netboxRetrieve(self):
        retrievalURL = self.netboxAPIurl + "?limit=100000"
        response = self.client.get(retrievalURL, headers=self.retrieveHeaders)
        jsonResponseDump = json.loads(response.text)
        if reQueryResponseFlag:
            print("+ API RESPONSE FOR REQUERY: \'" + retrievalURL + "\' Reads: \'" + str(jsonResponseDump) + "\'")
        return jsonResponseDump

reQueryEngineInstanceDict = collections.OrderedDict()
for rqType in dcimRequeryTypes:
    reQueryEngineInstanceDict[rqType] = apiEngine("dcim/", rqType)
    postCountDict[rqType] = 0
for rqType in tenancyRequeryTypes:
    reQueryEngineInstanceDict[rqType] = apiEngine("tenancy/", rqType)
    postCountDict[rqType] = 0

class QueryEngine:
    def __init__(self, sType, sSubType):
        self.dbConnector = mysql.connector.connect(
            host=dbHost,
            user=dbUser,
            passwd=dbPasswd,
            database=dbName
            )
        ### Instantiate cursor and apiEngine ###
        self.dbCursor = self.dbConnector.cursor()
        self.submitInstance = apiEngine(sType, sSubType)
   
    def dbQuery(self, queryString, outputMapping, slugEnable, migrationType):
        self.dbCursor.execute(queryString)
        rows = self.dbCursor.fetchall()
        objects_list = []
        for row in rows:
            d = collections.OrderedDict()
            for outParam in outputMapping:
                if isinstance(outputMapping[outParam], int):
                    if outParam == 'subdevice_role':
                        if row[(outputMapping[outParam])] == '1':
                            d[outParam] = True
                        elif row[(outputMapping[outParam])] == '0':
                            d[outParam] = False
                        else:
                            d[outParam] = "None"
                    else:
                        d[outParam] = row[(outputMapping[outParam])]
                else:
                    reQueryObject = row[outputMapping[outParam]['reQueryIndexHeader']]
                    reQuerySubType = outputMapping[outParam]['sSubType']
                    rqParamName = reQueryLookupDict[reQuerySubType]
                    #print("SEARCHING FOR:" + rqParamName + reQueryObject + " SEARCHING IN: " + reQuerySubType)
                    reQueryReturnDict = next(item for item in postResponses[reQuerySubType]['results'] if item[rqParamName] == reQueryObject)
                    #print(reQueryReturnDict)
                    reQueryResult = reQueryReturnDict['id']
                    #print("RQRESULT: " + str(reQueryResult))
                    d[outParam] = reQueryResult
            if slugEnable:
                d['slug'] = slugify(row[0])
            objects_list.append(d)
        if dcimOutputEnableFlag:
            for nbDataObject in objects_list:
                nbDataObjectJsonDump = json.dumps(nbDataObject, sort_keys=True, indent=4)
                self.submitInstance.netboxSubmit(nbDataObjectJsonDump)
                postCountDict[sSubType] = postCountDict[sSubType] + 1
        reQueryDump = reQueryEngineInstanceDict[sSubType].netboxRetrieve()
        return reQueryDump

postResponses = collections.OrderedDict()

with open(queryMapFile) as json_file:  
    data = json.load(json_file)
    reQueryLookupDict = data['reQueryLookupDict']
    for mType in data['results']:
        
        ### set parameters for the submission and query engine based on the map file ###
        migrationType = mType['querySubObjectID']
        sType = mType['sType']
        sSubType = mType['sSubType']
        queryString = mType['queryString']
        outputMapping = mType['outputMapping']
        slugEnable = mType['slugEnable']
        
        ### submission mapping debug code ###
        if ingestDebugFlag:
            print("\n")
            print("- MIGRATION DEBUG INFORMAION FOR: \'" + migrationType + "\'")
            print("   - API SUBMISSION URL: \n \t" + "-\'api/" + sType + sSubType + "\'")
            print("   - SQL QUERY STRING: \n \t \'-" + queryString + "\'")
            print("   - THE SLUG ENABLE FLAG IS SET TO: \n \t -\'" + str(slugEnable) + "\'")
            print("   - OUTPUT PARAMETER MAPPING: - [ Mapping Parameter : QueryIndex or sSubType : reQueryPointer (If Applicable) ]")
            for outParam in outputMapping:
                if isinstance(outputMapping[outParam], int):
                    print("\t" * 1 + " - \'" + outParam + "\' = \'" + str(outputMapping[outParam]) + "\'")
                else:
                    print("\t" * 1 + " - \'" + outParam + "\' = SST \'" + outputMapping[outParam]['sSubType'] + "\' @ \'" + str(outputMapping[outParam]['reQueryIndexHeader']) + "\'")
        
        ### code for submitting the request group ###    
        queryEngineInstance = QueryEngine(sType, sSubType)
        postResponses[sSubType] = queryEngineInstance.dbQuery(queryString, outputMapping, slugEnable, migrationType)
        print("Successfully Posted: " + str(postCountDict[sSubType]) + "Items for type: " + str(sSubType))