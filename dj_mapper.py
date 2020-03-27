#! /usr/bin/env python3

import os
import sys
import argparse
import signal
import time
from datetime import datetime, timedelta
import xml.etree.ElementTree as etree
import json
import random
import re

#--import the base mapper library and variants
try: 
    import base_mapper
except: 
    print('')
    print('Please export PYTHONPATH=$PYTHONPATH:<path to mapper-base project>')
    print('')
    sys.exit(1)
baseLibrary = base_mapper.base_library(os.path.abspath(base_mapper.__file__).replace('base_mapper.py','base_variants.json'))
if not baseLibrary.initialized:
    sys.exit(1)

#----------------------------------------
def pause(question='PRESS ENTER TO CONTINUE ...'):
    """ pause for debug purposes """
    try: response = input(question)
    except KeyboardInterrupt:
        response = None
        global shutDown
        shutDown = True
    return response

#----------------------------------------
def signal_handler(signal, frame):
    print('USER INTERUPT! Shutting down ... (please wait)')
    global shutDown
    shutDown = True
    return
        
#----------------------------------------
def updateStat(cat1, cat2, example = None):
    if cat1 not in statPack:
        statPack[cat1] = {}
    if cat2 not in statPack[cat1]:
        statPack[cat1][cat2] = {}
        statPack[cat1][cat2]['count'] = 0

    statPack[cat1][cat2]['count'] += 1
    if example:
        if 'examples' not in statPack[cat1][cat2]:
            statPack[cat1][cat2]['examples'] = []
        if example not in statPack[cat1][cat2]['examples']:
            if len(statPack[cat1][cat2]['examples']) < 5:
                statPack[cat1][cat2]['examples'].append(example)
            else:
                randomSampleI = random.randint(2,4)
                statPack[cat1][cat2]['examples'][randomSampleI] = example
    return

#----------------------------------------
def getAttr (segment, tagName):
    """ get an xml element text value """
    try: value = segment.attrib[tagName]
    except: value = None
    else: 
        if len(value) == 0:
            value = None
    return value

#----------------------------------------
def getValue (segment, tagName = None):
    """ get an xml element text value """
    try: 
        if tagName: 
            value = segment.find(tagName).text.strip()
        else:
            value = segment.text.strip()
    except: value = None
    else: 
        if len(value) == 0:
            value = None
    return value

#----------------------------------------
def idNoteParse(notes, codeType):

    #--check if enclosed in parens
    notes = notes.lower().replace('.','')
    groupedStrings = re.findall('\(.*?\)',notes)
    for maybeCountry in groupedStrings:
        maybeCountry = maybeCountry[1:len(maybeCountry)-1]
        isoCountry = baseLibrary.isoCountryCode(maybeCountry) if codeType == 'country' else baseLibrary.isoStateCode(maybeCountry)
        if isoCountry:
            return isoCountry
        elif ',' in maybeCountry:
            countryName = maybeCountry[maybeCountry.find(',')+1:].strip()
            isoCountry = baseLibrary.isoCountryCode(maybeCountry) if codeType == 'country' else baseLibrary.isoStateCode(maybeCountry)
            if isoCountry:
                return isoCountry

    #--look for various labels
    tokenList = []
    if 'country of issue:' in notes:
        tokenList = notes[notes.find('country of issue:')+17:].strip().split()
    else:  #or try the whole string
        tokenList = notes.strip().split()

    #--if single token (just confirm or deny)
    if len(tokenList) == 1:
        if tokenList[0][-1] in (',', ';', ':'):
            tokenList[0] = tokenList[0][0:-1]
        maybeCountry = tokenList[0]
        isoCountry = baseLibrary.isoCountryCode(maybeCountry) if codeType == 'country' else baseLibrary.isoStateCode(maybeCountry)
        if isoCountry:
            return isoCountry
        else: 
            return None

    priorToken1 = ''
    priorToken2 = ''
    priorToken3 = ''
    maybeCountry = ''
    for currentToken in tokenList:
        if currentToken[-1] in (',', ';', ':'):
            currentToken = currentToken[0:-1] 

        maybeCountry = currentToken
        isoCountry0 = baseLibrary.isoCountryCode(maybeCountry) if codeType == 'country' else baseLibrary.isoStateCode(maybeCountry)
        isoCountry1 = None
        isoCountry2 = None
        isoCountry3 = None

        if priorToken1:
            maybeCountry = priorToken1 + ' ' + currentToken
            isoCountry1 = baseLibrary.isoCountryCode(maybeCountry) if codeType == 'country' else baseLibrary.isoStateCode(maybeCountry)
        if priorToken2:
            maybeCountry = priorToken2 + ' ' + priorToken1 + ' ' + currentToken
            isoCountry2 = baseLibrary.isoCountryCode(maybeCountry) if codeType == 'country' else baseLibrary.isoStateCode(maybeCountry)
        if priorToken3:
            maybeCountry = priorToken3 + ' ' + priorToken2 + ' ' + priorToken1 + ' ' + currentToken
            isoCountry3 = baseLibrary.isoCountryCode(maybeCountry) if codeType == 'country' else baseLibrary.isoStateCode(maybeCountry)

        if isoCountry0 and currentToken not in ('id', 'in','is','on','no','and'):  #--careful of connecting words here!
            return isoCountry0
        elif isoCountry1:
            return isoCountry1
        elif isoCountry2:
            return isoCountry2
        elif isoCountry3:
            return isoCountry3

        priorToken3 = priorToken2
        priorToken2 = priorToken1
        priorToken1 = currentToken

    return None

#----------------------------------------
def concatDateParts(day, month, year):
    #--15-mar-2010 is format
    fullDate = ''
    if day:
        fullDate += day + '-'
    if month:
        fullDate += month + '-'
    if year:
        fullDate += year
    return fullDate

#----------------------------------------
def g2Mapping(masterRecord, recordType):

    #--header
    jsonData = {}
    jsonData['DATA_SOURCE'] = dataSource
    jsonData['RECORD_ID'] = masterRecord.attrib['id']
    
    jsonData['LAST_UPDATE'] = masterRecord.attrib['date']
    jsonData['STATUS'] = getValue(masterRecord, 'ActiveStatus')
    jsonData['DJ_PROFILE_ID'] = masterRecord.attrib['id']

    gender = getValue(masterRecord, 'Gender')
    if gender:
        jsonData['GENDER'] = gender
        updateStat('ATTRIBUTE', 'GENDER')

    deceased = getValue(masterRecord, 'Deceased')
    if deceased == 'Yes':
        jsonData['DECEASED'] = deceased
        updateStat('OTHER', 'DECEASED', deceased)
    
    #--names
    # <NameType NameTypeID="1" RecordType="Person">Primary Name</NameType>
    # <NameType NameTypeID="2" RecordType="Person">Also Known As</NameType>
    # <NameType NameTypeID="3" RecordType="Person">Low Quality AKA</NameType>
    # <NameType NameTypeID="4" RecordType="Person">Maiden Name</NameType>
    # <NameType NameTypeID="5" RecordType="Person">Formerly Known As</NameType>
    # <NameType NameTypeID="6" RecordType="Person">Spelling Variation</NameType>
    # <NameType NameTypeID="7" RecordType="Entity">Primary Name</NameType>
    # <NameType NameTypeID="8" RecordType="Entity">Also Known As</NameType>
    # <NameType NameTypeID="9" RecordType="Entity">Formerly Known As</NameType>
    # <NameType NameTypeID="10" RecordType="Entity">Spelling Variation</NameType>
    # <NameType NameTypeID="11" RecordType="Entity">Low Quality AKA</NameType>
    orgPersonNameConflict = False
    thisList = []
    for nameRecord in masterRecord.findall('NameDetails/Name'):
        nameType = nameRecord.attrib['NameType'][0:25]
        if 'PRIMARY' in nameType.upper():
            nameType = 'PRIMARY'

        for nameValue in nameRecord.findall('NameValue'):
            nameStr = ''
            name = {}
            name['NAME_TYPE'] = nameType
            updateStat('NAME_TYPE', nameType)

            nameOrg = getValue(nameValue, 'EntityName')
            if nameOrg:
                if len(nameOrg.split()) > 16:
                    updateStat('TRUNCATIONS', 'longNameOrgCnt', nameOrg)
                    nameOrg = ' '.join(nameOrg.split()[:16])
                name['NAME_ORG'] = nameOrg
                nameStr = nameOrg

            nameLast = getValue(nameValue, 'Surname')
            if nameLast:
                if len(nameLast.split()) > 5:
                    updateStat('TRUNCATIONS', 'longNameLastCnt', nameLast)
                    nameLast = ' '.join(nameLast.split()[:5])
                name['NAME_LAST'] = nameLast
                nameStr = nameLast

            nameMaiden = getValue(nameValue, 'MaidenName')
            if nameMaiden and not nameLast:  #--either Surname or MaidenName will be populated
                if len(nameMaiden.split()) > 5:
                    updateStat('TRUNCATIONS', 'longNameMaidenCnt', nameMaiden)
                    nameMaiden = ' '.join(nameMaiden.split()[:5])
                name['NAME_LAST'] = nameMaiden
                nameStr = nameLast

            nameFirst = getValue(nameValue, 'FirstName')
            if nameFirst:
                if len(nameFirst.split()) > 5:
                    updateStat('TRUNCATIONS', 'longNameFirstCnt', nameFirst)
                    nameFirst = ' '.join(nameFirst.split()[:5])
                name['NAME_FIRST'] = nameFirst
                nameStr += (' '+nameFirst)

            nameMiddle = getValue(nameValue, 'MiddleName')
            if nameMiddle:
                if len(nameMiddle.split()) > 5:
                    updateStat('TRUNCATIONS', 'longNameMiddleCnt', nameMiddle)
                    nameMiddle = ' '.join(nameMiddle.split()[:5])
                name['NAME_MIDDLE'] = nameMiddle
                nameStr += (' '+nameMiddle)

            namePrefix = getValue(nameValue, 'TitleHonorific')
            if namePrefix:
                name['NAME_PREFIX'] = namePrefix
            nameSuffix = getValue(nameValue, 'Suffix')
            if nameSuffix:
                name['NAME_SUFFIX'] = nameSuffix
            
            thisList.append(name)
            
            #--check for a name conflict
            if (recordType == 'PERSON' and 'NAME_ORG' in name) or (recordType != 'PERSON' and 'NAME_LAST' in name):
                orgPersonNameConflict = True

            #--duplicate this name segment for original script version if supplied
            originalScriptName = getValue(nameValue, 'OriginalScriptName')
            if originalScriptName:
                name = {}
                updateStat('NAME_TYPE', 'OriginalScriptName')
                name['NAME_TYPE'] = 'OriginalScriptName'
                name['NAME_FULL'] = originalScriptName
                thisList.append(name)
            
    if thisList:
        jsonData['NAMES'] = thisList
    if orgPersonNameConflict:
        print('warning: person and org names on record %s' % jsonData['RECORD_ID'])
    
    #--dates
    # <DateType Id="1" RecordType="Person" name="Date of Birth"/>
    # <DateType Id="2" RecordType="Person" name="Deceased Date"/>
    # <DateType Id="3" RecordType="Entity" name="Date of Registration"/>
    thisList = []
    for dateRecord in masterRecord.findall('DateDetails/Date'):

        dateType = dateRecord.attrib['DateType']
        if dateType == 'Date of Birth':
            dateType = 'DATE_OF_BIRTH'
        elif dateType == 'Deceased Date':
            dateType = 'DATE_OF_DEATH'
        elif dateType == 'Date of Registration':
            dateType = 'REGISTRATION_DATE'

        for dateValue in dateRecord.findall('DateValue'):
            day = getAttr(dateValue, 'Day')
            month = getAttr(dateValue, 'Month')
            year = getAttr(dateValue, 'Year')
            thisDate = concatDateParts(day, month, year)
            if dateType == 'DATE_OF_BIRTH':
                outputFormat = '%Y-%m-%d'
                if not day and not month:
                    updateStat('DOB_DATA', 'year only', thisDate)
                elif year and month and not day:
                    updateStat('DOB_DATA', 'year/month only', thisDate)
                elif month and day and not year:
                    updateStat('DOB_DATA', 'month/day only', thisDate)
                else:
                    updateStat('DOB_DATA', 'full', thisDate)

                formattedDate = baseLibrary.formatDate(thisDate)
                if formattedDate:
                    thisList.append({dateType: formattedDate})
            else:
                jsonData[dateType] = thisDate
            updateStat('ATTRIBUTE', dateType, thisDate)
    if thisList:
        jsonData['DATES'] = thisList
            
    #--addresses
    thisList = []
    for addrRecord in masterRecord.findall('Address'):
        address = {}
        addrLine = getValue(addrRecord, 'AddressLine')
        if addrLine:
            if len(addrLine.split()) > 16:
                updateStat('TRUNCATIONS', 'longAddrLineCnt', addrLine)
                addrLine = ' '.join(addrLine.split()[:16])
            address['ADDR_LINE1'] = addrLine
        addrCity = getValue(addrRecord, 'AddressCity')
        if addrCity:
            address['ADDR_CITY'] = addrCity
        addrCountry = getValue(addrRecord, 'AddressCountry')
        if addrCountry:
            address['ADDR_COUNTRY'] = countryCodes[addrCountry] if addrCountry in countryCodes else addrCountry
            isoCountry = baseLibrary.isoCountryCode(address['ADDR_COUNTRY'])
            if isoCountry:
                address['ADDR_COUNTRY'] = isoCountry

        thisList.append(address)
        updateStat('ADDRESS', 'UNTYPED')

    if thisList:
        jsonData['ADDRESSES'] = thisList

    #--company details (address/website)
    thisList1 = []
    thisList2 = []
    for addrRecord in masterRecord.findall('CompanyDetails'):
        address = {}
        address['ADDR_TYPE'] = 'BUSINESS'
        addrLine = getValue(addrRecord, 'AddressLine')
        if addrLine:
            if len(addrLine.split()) > 16:
                updateStat('TRUNCATIONS', 'longAddrLineCnt', addrLine)
                addrLine = ' '.join(addrLine.split()[:16])
            address['ADDR_LINE1'] = addrLine
        addrCity = getValue(addrRecord, 'AddressCity')
        if addrCity:
            address['ADDR_CITY'] = addrCity
        addrCountry = getValue(addrRecord, 'AddressCountry')
        if addrCountry:
            address['ADDR_COUNTRY'] = countryCodes[addrCountry] if addrCountry in countryCodes else addrCountry
            isoCountry = baseLibrary.isoCountryCode(address['ADDR_COUNTRY'])
            if isoCountry:
                address['ADDR_COUNTRY'] = isoCountry

        thisList1.append(address)
        updateStat('ADDRESS', 'BUSINESS')
            
        url = getValue(addrRecord, 'URL')
        if url:
            thisList2.append({'WEBSITE_ADDRESS': url})
            updateStat('ATTRIBUTE', 'WEBSITE_ADDRESS')
            
    if thisList1:
        jsonData['COMPANY_ADDRESSES'] = thisList1
    if thisList2:
        jsonData['COMPANY_WEBSITES'] = thisList2
            
    #--countries
    thisList1 = []
    for birthPlaceRecord in masterRecord.findall('BirthPlace/Place'):
        birthPlace = birthPlaceRecord.attrib['name']
        thisList1.append({'PLACE_OF_BIRTH': birthPlace})
        updateStat('ATTRIBUTE', 'PLACE_OF_BIRTH')
 
    for countryRecord in masterRecord.findall('CountryDetails/Country'):
        countryType = countryRecord.attrib['CountryType']
        if countryType == 'Citizenship':
            attributeType = 'CITIZENSHIP'
        else:
            if countryType == 'REGISTRATION':
                usageType = 'REGISTRATION'
            elif countryType == 'Resident of':
                usageType = 'RESIDENT'
            elif countryType == 'Jurisdiction':
                usageType = 'JURISDICTION'
            elif countryType == 'Country of Affiliation':
                usageType = 'AFFILIATED'
            elif countryType == 'Enhanced Risk Country':
                usageType = 'RISK'
            else:
                usageType = 'OTHER'
            attributeType = usageType + '_COUNTRY_OF_ASSOCIATION'

        itemNum = 0
        for countryValue in countryRecord.findall('CountryValue'):
            countryCode = countryValue.attrib['Code']
            countryName = countryCodes[countryCode] if countryCode in countryCodes else countryCode
            isoCountry = baseLibrary.isoCountryCode(countryName)
            if isoCountry:
                countryName = isoCountry

            thisList1.append({attributeType: countryName})
            updateStat('COUNTRIES', attributeType, countryName)
 
    if thisList1:
        jsonData['COUNTRIES'] = thisList1

    #--identifiers
    itemNum = 0
    thisList = []
    for idRecord in masterRecord.findall('IDNumberTypes/ID'):
        idType = idRecord.attrib['IDType']
        for idValue in idRecord.findall('IDValue'):
            idNumber = getValue(idValue)
            idNotes = getAttr(idValue, 'IDnotes')
            if not idNotes:
                idNotes = ''

            attrType1 = None
            attrType2 = None
            countryCheck = 0

            if idType.upper() == 'SOCIAL SECURITY NO.':
                attrType1 = 'SSN_NUMBER'
            elif idType.upper() == 'PASSPORT NO.':
                attrType1 = 'PASSPORT_NUMBER'
                attrType2 = 'PASSPORT_COUNTRY'
                countryCheck = 1
            elif idType.upper() == 'DRIVING LICENCE NO.':
                attrType1 = 'DRIVERS_LICENSE_NUMBER'
                attrType2 = 'DRIVERS_LICENSE_STATE'
                countryCheck = 2
            elif idType.upper() == 'NATIONAL ID': 
                attrType1 = 'NATIONAL_ID_NUMBER'
                attrType2 = 'NATIONAL_ID_COUNTRY'
                countryCheck = 1
            elif idType.upper() == 'NATIONAL TAX NO.':
                attrType1 = 'TAX_ID_NUMBER'
                attrType2 = 'TAX_ID_COUNTRY'
                countryCheck = 1
            elif idType.upper() == 'COMPANY IDENTIFICATION NO.':
                attrType1 = 'COMPANY_ID_NUMBER'
                attrType2 = 'COMPANY_ID_COUNTRY'
                countryCheck = 1
            elif idType.upper() == 'DUNS NUMBER':
                attrType1 = 'DUNS_NUMBER'
            elif idType.upper() == 'OFAC UNIQUE ID':
                attrType1 = 'OFAC_ID'
            elif idType.upper() == 'NATIONAL PROVIDER IDENTIFIER (NPI)' or idNotes.startswith('NPI') or '(NPI)' in idNotes.upper():
                attrType1 = 'NPI_NUMBER'
            elif idType.upper() == 'LEGAL ENTITY IDENTIFIER (LEI)':
                attrType1 = 'LEI_NUMBER'
            elif idType.upper() == 'NATIONAL CRIMINAL IDENTIFICATION CODE (USA)' or '(NCIC)' in idNotes.upper():
                attrType1 = 'NCIC_NUMBER'
            elif idType.upper() == 'CENTRAL REGISTRATION DEPOSITORY (CRD)':
                attrType1 = 'CRD_NUMBER'
            elif idType.upper() == 'INTERNATIONAL MARITIME ORGANIZATION (IMO) SHIP NO.':
                attrType1 = 'IMO_NUMBER'
            elif idType.upper() == 'INTERNATIONAL SECURITIES IDENTIFICATION NUMBER (ISIN)':
                attrType1 = 'ISIN_NUMBER'
            elif idType.upper() == 'OTHERS' and idNotes.upper() == 'MMSI':
                attrType1 = 'MMSI_NUMBER'
            elif '(MSN)' in idType.upper():
                attrType1 = 'AIRCRAFT_MSN'
            elif idType.upper() == 'OTHERS' and 'AIRCRAFT TAIL NUMBER' in idNotes.upper():
                attrType1 = 'AIRCRAFT_TAIL_NUMBER'
            else:
                attrType1 = None

            #--if mapped
            if attrType1:

                #--parse notes for a country or state code
                isoCode = None
                if idNotes:

                    #--try for country code
                    if countryCheck:
                        isoCode = idNoteParse(idNotes, 'country')

                    #--try for US state code
                    if countryCheck == 2 and (isoCode in ('USA', 'US') or not isoCode):
                        isoCode = idNoteParse(idNotes, 'state')

                #--create the identity structure
                idDict = {}
                idDict[attrType1] = idNumber
                if attrType2 and isoCode: #--the notes should contain a country or a state
                    idDict[attrType2] = isoCode
                thisList.append(idDict)
                updateStat('ID_TYPE', '%s | %s' % (attrType1, isoCode), idNumber)

            #--un-mapped
            else:
                updateStat('UNKNOWN', '%s | %s' % (idType, idNotes), idNumber)
                itemNum += 1
                jsonData['ID%s' % itemNum] = idType + ' = ' + idNumber + ((' ' + idNotes) if idNotes else '')
            
    if thisList:
        jsonData['IDENTIFIERS'] = thisList

    #--descriptions
    itemNum = 0
    for descriptionRecord in masterRecord.findall('Descriptions/Description'):
        description1Code = None
        description2Code = None
        description3Code = None
        try: 
            description1 = '%s=%s' % (descriptionRecord.attrib['Description1'], description1Codes[descriptionRecord.attrib['Description1']])
            description1Code = descriptionRecord.attrib['Description1']
        except: description1 = ''
        try: 
            description2 = '%s=%s' % (descriptionRecord.attrib['Description2'], description2Codes[descriptionRecord.attrib['Description2']])
            description2Code = descriptionRecord.attrib['Description2']
        except: description2 = ''
        try: 
            description3 = '%s=%s' % (descriptionRecord.attrib['Description3'], description3Codes[descriptionRecord.attrib['Description3']])
            description3Code = description3Codes[descriptionRecord.attrib['Description3']].upper()
        except: description3 = ''
        if description1 or description2 or description3:
            itemNum += 1
            description = description1
            description += (' | ' if description2 else '') + description2
            description += (' | ' if description3 else '') + description3
            jsonData["Description%s" % itemNum] = description
            updateStat('DESCRIPTIONS', description, jsonData['RECORD_ID'])

        #--record type reclassifications
        if description3Code == 'SHIP':
            recordType = 'VESSEL'
        if description3Code == 'AIRCRAFT':
            recordType = 'AIRCRAFT'

    #--roles
    for roleRecord in masterRecord.findall('RoleDetail/Roles'):
        itemNum = 0
        roleType = roleRecord.attrib['RoleType']
        for occTitle in roleRecord.findall('OccTitle'):
            itemNum += 1
            fromDate = concatDateParts(getAttr(occTitle, 'SinceDay'), getAttr(occTitle, 'SinceMonth'), getAttr(occTitle, 'SinceYear'))
            thruDate = concatDateParts(getAttr(occTitle, 'ToDay'), getAttr(occTitle, 'ToMonth'), getAttr(occTitle, 'SinceYear'))
            thisRole = getValue(occTitle)
            if fromDate:
                thisRole += ' From ' + fromDate
            if thruDate:
                thisRole += ' To ' + thruDate
            jsonData[roleType + str(itemNum)] = thisRole
            updateStat('OTHER', 'ROLES', thisRole)

    #--references
    itemNum = 0
    for referenceRecord in masterRecord.findall('SanctionsReferences/Reference'):
        itemNum += 1
        referenceName = referenceCodes[getValue(referenceRecord)]
        jsonData["Reference%s" % itemNum] = referenceName
        updateStat('OTHER', 'REFERENCES', referenceName)
        
    #--sources
    if False:  #--disabled to keep reports smaller
        itemNum = 0
        for sourceRecord in masterRecord.findall('SourceDescription/Source'):
            sourceName = sourceRecord.attrib['name']
            #--updateStat('source-' + sourceName) <--too many of these to log
            jsonData["Source%s" % itemNum] = sourceName

    #--disclosed relationships
    thisList = []
    thisId = jsonData['RECORD_ID']
    if thisId in relationships:
        for relationship in relationships[thisId]:
            #--disclosed relationship
            relType = relationCodes[relationship['code']].replace(' ', '_').replace('-','_')
            #--get other side
            otherId = relationship['id']
            relType1 = None
            if otherId in relationships:
                for relationship1 in relationships[otherId]:
                    if relationship1['id'] == thisId:
                        relType1 = relationCodes[relationship1['code']].replace(' ', '_').replace('-','_')
                        break
            relKey = '-'.join(sorted([thisId, otherId]))
            if relType1 and relType1 != relType:
                relType = '/'.join(sorted([relType, relType1]))
            #--create the relationship
            thisRecord = {}
            if noRelationships:
                thisRecord['Related to'] = '%s | %s | %s' % (dataSource, otherId, relType)
            else:  
                thisRecord['RELATIONSHIP_TYPE'] = relType
                thisRecord['RELATIONSHIP_KEY'] = relKey
            updateStat('RELATIONSHIPS', relType)
            thisList.append(thisRecord)
            #--group association name
            if recordType == 'PERSON' and relationship['id'] in entityNames:
                thisRecord = {}
                #thisRecord[relType + '_GROUP_ASSOCIATION_TYPE'] = 'ORG'
                thisRecord[relType + '_GROUP_ASSOCIATION_ORG_NAME'] = entityNames[relationship['id']]
                thisList.append(thisRecord)
                updateStat('GROUP_ASSOCIATION', 'NAME', relType)
            #--group association IDs
            if recordType == 'PERSON' and relationship['id'] in entityDuns:
                thisRecord = {}
                thisRecord[relType + '_GROUP_ASSN_ID_TYPE'] = 'DUNS'
                thisRecord[relType + '_GROUP_ASSN_ID_NUMBER'] = entityDuns[relationship['id']]
                thisList.append(thisRecord)
                updateStat('GROUP_ASSOCIATION', 'DUNS', relType)
    if thisList:
        jsonData['RELATIONSHIPS'] = thisList
        
    #--assign the entity and record type
    jsonData['ENTITY_TYPE'] = recordType.upper()                                                                                                                                
    jsonData['RECORD_TYPE'] = recordType.upper()
    updateStat('ENTITY_TYPE', jsonData['ENTITY_TYPE'])

    #--add composite keys
    if addCompositeKeys:
        jsonData = baseLibrary.jsonUpdater(jsonData)

    return jsonData
        
#----------------------------------------
if __name__ == "__main__":
    appPath = os.path.dirname(os.path.abspath(sys.argv[0]))

    global shutDown
    shutDown = False
    signal.signal(signal.SIGINT, signal_handler)
    procStartTime = time.time()
    progressInterval = 10000

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-i', '--input_file', default=os.getenv('input_file'.upper(), None), type=str, help='A Dow Jones xml file for PFA or HRF.')
    argparser.add_argument('-o', '--output_file', default=os.getenv('output_file'.upper(), None), type=str, help='output filename, defaults to input file name with a .json extension.')
    argparser.add_argument('-l', '--log_file', default=os.getenv('log_file'.upper(), None), type=str, help='optional statistics filename (json format).')
    argparser.add_argument('-d', '--data_source', default=os.getenv('data_source'.upper(), None), type=str, help='please use DJ-PFA or DJ-HRF based on the type of file.')
    args = argparser.parse_args()
    inputFileName = args.input_file
    outputFileName = args.output_file
    logFile = args.log_file
    dataSource = args.data_source

    #--deprecated arguments
    noRelationships = False
    addCompositeKeys = False
    
    if not inputFileName:
        print('')
        print('Please select a dow jones xml input file')
        print('')
        sys.exit(1)

    if not os.path.exists(inputFileName):
        print('')
        print('Input file %s not found!' % inputFileName)
        print('')
        sys.exit(1)
    
    #--default and validate the data source
    if not dataSource and 'PFA' in inputFileName.upper():
        dataSource = 'DJ-PFA'
    elif not dataSource and 'HRF' in inputFileName.upper():
        dataSource = 'DJ-HRF'
    if not dataSource or dataSource.upper() not in ('DJ-PFA', 'DJ-HRF'):
        print('')
        print('Please specify either DJ-PFA or DJ-HRF as the data source')
        print('')
        sys.exit(1)
    else:
        dataSource = dataSource.upper()
        
    if not (outputFileName):
        print('')
        print('Please supply an output file name.')
        print('')

    #--open output file
    try: outputFileHandle = open(outputFileName, "w", encoding='utf-8')
    except IOError as err:
        print('')
        print('Could not open output file %s for writing' % outputFileName)
        print(' %s' % err)
        print('')
        sys.exit(1)

    #--initialize some stats
    recordCnt = 0
    personCnt = 0
    entityCnt = 0
    statPack = {}
    
    #--initialize code dictionaries
    countryCodes = {}
    description1Codes = {}
    description2Codes = {}
    description3Codes = {}
    referenceCodes = {}
    relationCodes = {}
    relationships = {}
    entityNames = {}
    entityDuns = {}

    #--iterate through the xml file serially as it is huge! 
    print('')
    print('Data source set to %s' % dataSource)
    print('')
    print('Reading from: %s ...' % inputFileName)
    xmlReader = etree.iterparse(inputFileName, events=("start", "end"))
    for event, node in xmlReader:
        if event == 'end':

            if node.tag == 'CountryList':
                print('loading %s ...' % node.tag) 
                for record in node.findall('CountryName'):
                    countryCodes[getAttr(record, 'code')] = getAttr(record, 'name')
                node.clear()
                
            elif node.tag == 'Description1List':
                print('loading %s ...' % node.tag) 
                for record in node.findall('Description1Name'):
                    description1Codes[getAttr(record, 'Description1Id')] = getValue(record)
                node.clear()

            elif node.tag == 'Description2List':
                print('loading %s ...' % node.tag) 
                for record in node.findall('Description2Name'):
                    description2Codes[getAttr(record, 'Description2Id')] = getValue(record)
                node.clear()

            elif node.tag == 'Description3List':
                print('loading %s ...' % node.tag) 
                for record in node.findall('Description3Name'):
                    description3Codes[getAttr(record, 'Description3Id')] = getValue(record)
                node.clear()

            elif node.tag == 'SanctionsReferencesList':
                print('loading %s ...' % node.tag) 
                for record in node.findall('ReferenceName'):
                    referenceCodes[getAttr(record, 'code')] = getAttr(record, 'name')
                node.clear()

            elif node.tag == 'RelationshipList':
                print('loading %s ...' % node.tag) 
                for record in node.findall('Relationship'):
                    relationCodes[getAttr(record, 'code')] = getAttr(record, 'name').replace('_', '-')
                node.clear()
                    
            elif node.tag == 'Associations':
                print('loading %s ...' % node.tag) 
                for record in node.findall('PublicFigure'):
                    id = getAttr(record, 'id')
                    relationships[id] = []
                    for record1 in record.findall('Associate'):
                        relationships[id].append({'id': getAttr(record1, 'id'), 'code': getAttr(record1, 'code')})
                for record in node.findall('SpecialEntity'):
                    id = getAttr(record, 'id')
                    relationships[id] = []
                    for record1 in record.findall('Associate'):
                        relationships[id].append({'id': getAttr(record1, 'id'), 'code': getAttr(record1, 'code')})
                node.clear()
        
            elif node.tag == 'Entity':
                id = getAttr(node, 'id')
                for nameRecord in node.findall('NameDetails/Name'):
                    if nameRecord.attrib['NameType'] == 'Primary Name':
                        for nameValue in nameRecord.findall('NameValue'):
                            nameOrg = getValue(nameValue, 'EntityName')
                            if nameOrg:
                                entityNames[id] = nameOrg
                                break
                        break
                for idRecord in node.findall('IDNumberTypes/ID'):
                    if idRecord.attrib['IDType'] == 'DUNS Number':
                        for idValue in idRecord.findall('IDValue'):
                            idNumber = getValue(idValue)
                            if idNumber: 
                                entityDuns[id] = idNumber
                                break
                        break

                node.clear()

            elif node.tag in ('Person'):
                node.clear()

    #print('countryCodes', len(countryCodes))
    #print('description1Codes', len(description1Codes))
    #print('description2Codes', len(description2Codes))
    #print('description3Codes', len(description3Codes))
    #print('referenceCodes', len(referenceCodes))
    #print('relationCodes', len(relationCodes))
    #print('relationships', len(relationships))
    #print('entityNames', len(entityNames))
    #sys.exit(1)
    
    #--go through a second time to process the records
    print('')
    print('processing records ...')
    xmlReader = etree.iterparse(inputFileName, events=("start", "end"))
    for event, node in xmlReader:
        if event == 'end' and node.tag in ('Person','Entity'):
            if node.tag == 'Person':
                jsonData = g2Mapping(node, 'PERSON')
                personCnt += 1 
            else:
                jsonData = g2Mapping(node, 'ORGANIZATION')
                entityCnt += 1
            msg = json.dumps(jsonData, ensure_ascii=False)

            try: outputFileHandle.write(msg + '\n')
            except IOError as err:
                print('')
                print('Could not write to %s' % outputFileName)
                print(' %s' % err)
                print('')
                shutDown = True

            node.clear()
 
            if shutDown: 
                break

            recordCnt += 1 
            if recordCnt % progressInterval == 0:
                print('%s rows processed' % recordCnt)
        
    outputFileHandle.close()
    
    print('%s rows processed, completed!' % recordCnt)
    print('%s persons' % personCnt)
    print('%s entities' % entityCnt)
    #print('%s longNameOrgCnt' % longNameOrgCnt)
    #print('%s longNameLastCnt' % longNameLastCnt)
    #print('%s longNameMaidenCnt' % longNameMaidenCnt)
    #print('%s longNameFirstCnt' % longNameFirstCnt)
    #print('%s longNameMiddleCnt' % longNameMiddleCnt)
    #print('%s longAddrLineCnt' % longAddrLineCnt)
    #print('')


    #--write statistics file
    if logFile: 
        print('')
        statPack['BASE_LIBRARY'] = baseLibrary.statPack
        with open(logFile, 'w') as outfile:
            json.dump(statPack, outfile, indent=4, sort_keys = True)    
        print('Mapping stats written to %s' % logFile)
    
    print('')
    elapsedMins = round((time.time() - procStartTime) / 60, 1)
    if shutDown == 0:
        print('Process completed successfully in %s minutes!' % elapsedMins)
    else:
        print('Process aborted after %s minutes!' % elapsedMins)
    print('')
    
    sys.exit(0)
