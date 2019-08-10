#! /usr/bin/env python3

import os
import sys
import argparse
from datetime import datetime
import json
import xml.etree.ElementTree as etree
import re
import random

#----------------------------------------
def pause(question='PRESS ENTER TO CONTINUE ...'):
    """ pause for debug purposes """
    if sys.version[0] == '2':
        response = raw_input(question)
    else:
        response = input(question)
    return response

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
def formatDate(inStr):
    """ format a date as yyyy-mm-dd """
    #--bypass if not complete
    outStr = inStr
    #if len(inStr) >= 6:

    formatList = []
    formatList.append("%Y-%m-%d")
    formatList.append("%m/%d/%Y")
    formatList.append("%m/%d/%y")
    formatList.append("%d %b %Y")
    formatList.append("%d %m %Y")
    #formatList.append("%Y")
    #formatList.append("CIRCA %Y")

    for format in formatList:
        #outStr = datetime.strftime(datetime.strptime(inStr, format), '%Y-%m-%d')
        try: outStr = datetime.strftime(datetime.strptime(inStr, format), '%Y-%m-%d')
        except: pass
        else: 
            break

    return outStr

#----------------------------------------
def convertNameType(inValue):
    if inValue.upper() == 'PRIMARY NAME':
        outValue = 'PRIMARY'
    else:
        outValue = inValue[0:25]
    return outValue

#----------------------------------------
def convertNameType(inValue):
    if inValue.upper() == 'PRIMARY NAME':
        outValue = 'PRIMARY'
    else:
        outValue = inValue[0:25]
    return outValue

#----------------------------------------
def convertDateType(inValue):
    if inValue.upper() == 'DATE OF BIRTH':
        outValue = 'DATE_OF_BIRTH'
    elif inValue.upper() == 'DECEASED DATE':
        outValue = 'DATE_OF_DEATH'
    elif inValue.upper() == 'DATE OF REGISTRATION':
        outValue = 'REGISTRATION_DATE'
    else:
        outValue = inValue
    return outValue

#----------------------------------------
def idNoteParse(notes, isoCodes):

    #--check if enclosed in parens
    notes = notes.lower().replace('.','')
    groupedStrings = re.findall('\(.*?\)',notes)
    for maybeCountry in groupedStrings:
        maybeCountry = maybeCountry[1:len(maybeCountry)-1]
        if maybeCountry in isoCodes:
            return isoCodes[maybeCountry]
        elif ',' in maybeCountry:
            countryName = maybeCountry[maybeCountry.find(',')+1:].strip()
            if countryName in isoCodes:
                return isoCodes[countryName]

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
        if tokenList[0] in isoCodes:
            return isoCodes[tokenList[0]]
        else: 
            return None

    priorToken1 = ''
    priorToken2 = ''
    priorToken3 = ''
    maybeCountry = ''
    for currentToken in tokenList:
        if currentToken[-1] in (',', ';', ':'):
            currentToken = currentToken[0:-1] 
        if currentToken not in ('id', 'in','is','on','no','and') and currentToken in isoCodes:  #--careful of connecting words here!
            return isoCodes[currentToken]
        elif priorToken1 and priorToken1 + ' ' + currentToken in isoCodes:
            return isoCodes[priorToken1 + ' ' + currentToken]
        elif priorToken2 and (priorToken2 + ' ' + priorToken1 + ' ' + currentToken) in isoCodes:
            return isoCodes[priorToken2 + ' ' + priorToken1 + ' ' + currentToken]
        elif priorToken3 and (priorToken3 + ' ' + priorToken2 + ' ' + priorToken1 + ' ' + currentToken) in isoCodes:
            return isoCodes[priorToken3 + ' ' + priorToken2 + ' ' + priorToken1 + ' ' + currentToken]

        priorToken3 = priorToken2
        priorToken2 = priorToken1
        priorToken1 = currentToken

    return None

#----------------------------------------
def updateStat(cat1, cat2, example = None):
    if cat1 not in statPack:
        statPack[cat1] = {}
    if cat2 not in statPack[cat1]:
        statPack[cat1][cat2] = {}
        statPack[cat1][cat2]['count'] = 1

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
def concatDateParts(day, month, year):
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

    global longNameOrgCnt
    global longNameLastCnt
    global longNameMaidenCnt
    global longNameFirstCnt
    global longNameMiddleCnt
    global longAddrLineCnt
    
    #--initiailze composite key lists
    ckNameList = []
    isoCountriesList = []

    #--header
    jsonData = {}
    jsonData['DATA_SOURCE'] = dataSource
    jsonData['RECORD_ID'] = masterRecord.attrib['id']
    jsonData['ENTITY_TYPE'] = recordType.upper()
    jsonData['RECORD_TYPE'] = recordType.upper()
    updateStat('ENTITY_TYPE', jsonData['ENTITY_TYPE'])
    
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
        updateStat('USEFUL_DATA', 'DECEASED')
    
    #--names
    thisList = []
    for nameRecord in masterRecord.findall('NameDetails/Name'):
        nameType = convertNameType(nameRecord.attrib['NameType'])
        for nameValue in nameRecord.findall('NameValue'):
            name = {}
            name['NAME_TYPE'] = nameType
            updateStat('NAME_TYPE', nameType)

            nameOrg = getValue(nameValue, 'EntityName')
            if nameOrg:
                if len(nameOrg.split()) > 16:
                    nameOrg = ' '.join(nameOrg.split()[:16])
                    longNameOrgCnt += 1
                name['NAME_ORG'] = nameOrg

            nameLast = getValue(nameValue, 'Surname')
            if nameLast:
                if len(nameLast.split()) > 5:
                    nameLast = ' '.join(nameLast.split()[:5])
                    longNameLastCnt += 1
                name['NAME_LAST'] = nameLast

            nameMaiden = getValue(nameValue, 'MaidenName')
            if nameMaiden and not nameLast:  #--either Surname or MaidenName will be populated
                if len(nameMaiden.split()) > 5:
                    nameMaiden = ' '.join(nameMaiden.split()[:5])
                    longNameMaidenCnt += 1
                name['NAME_LAST'] = nameMaiden

            nameFirst = getValue(nameValue, 'FirstName')
            if nameFirst:
                if len(nameFirst.split()) > 5:
                    nameFirst = ' '.join(nameFirst.split()[:5])
                    longNameFirstCnt += 1
                name['NAME_FIRST'] = nameFirst

            nameMiddle = getValue(nameValue, 'MiddleName')
            if nameMiddle:
                if len(nameMiddle.split()) > 5:
                    nameMiddle = ' '.join(nameMiddle.split()[:5])
                    longNameMiddleCnt += 1
                name['NAME_MIDDLE'] = nameMiddle

            namePrefix = getValue(nameValue, 'TitleHonorific')
            if namePrefix:
                name['NAME_PREFIX'] = namePrefix
            nameSuffix = getValue(nameValue, 'Suffix')
            if nameSuffix:
                name['NAME_SUFFIX'] = nameSuffix
            
            thisList.append(name)
            
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
    
    #--dates
    thisList = []
    for dateRecord in masterRecord.findall('DateDetails/Date'):
        dateType = convertDateType(dateRecord.attrib['DateType'])
        for dateValue in dateRecord.findall('DateValue'):
            thisDate = concatDateParts(getAttr(dateValue, 'Day'), getAttr(dateValue, 'Month'), getAttr(dateValue, 'Year'))
            if dateType == 'DATE_OF_BIRTH':
                thisList.append({dateType: thisDate})
                updateStat('ATTRIBUTE', 'DATE_OF_BIRTH')
            else:
                jsonData[dateType] = thisDate
                updateStat('USEFUL_DATA', dateType)
    if thisList:
        jsonData['DATES'] = thisList
            
    #--addresses
    onlyCountryList = []
    thisList = []
    for addrRecord in masterRecord.findall('Address'):
        address = {}
        addrLine = getValue(addrRecord, 'AddressLine')
        if addrLine:
            if len(addrLine.split()) > 16:
                addrLine = ' '.join(addrLine.split()[:16])
                longAddrLineCnt += 1
            address['ADDR_LINE1'] = addrLine
        addrCity = getValue(addrRecord, 'AddressCity')
        if addrCity:
            address['ADDR_CITY'] = addrCity
        addrCountry = getValue(addrRecord, 'AddressCountry')
        if addrCountry:
            address['ADDR_COUNTRY'] = addrCountry
            if addrCountry.lower() in isoCountries: #--also map the code for matching
                isoCountriesList.append(isoCountries[addrCountry.lower()])

        if len(address) == 1 and list(address.keys())[0] == 'ADDR_COUNTRY':
            onlyCountryList.append(address['ADDR_COUNTRY'])
            updateStat('ADDRESS', 'country only')
        else:
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
                addrLine = ' '.join(addrLine.split()[:16])
                longAddrLineCnt += 1
            address['ADDR_LINE1'] = addrLine
        addrCity = getValue(addrRecord, 'AddressCity')
        if addrCity:
            address['ADDR_CITY'] = addrCity
        addrCountry = getValue(addrRecord, 'AddressCountry')
        if addrCountry:
            address['ADDR_COUNTRY'] = addrCountry
            if addrCountry.lower() in isoCountries: #--also map the code for matching
                isoCountriesList.append(isoCountries[addrCountry.lower()])
        if address:
            if len(address) == 1 and list(address.keys())[0] == 'ADDR_COUNTRY':
                onlyCountryList.append(address['ADDR_COUNTRY'])
                updateStat('ADDRESS', 'country only')
            else:
                thisList1.append(address)
                updateStat('ADDRESS', 'UNTYPED')
            
        url = getValue(addrRecord, 'URL')
        if url:
            thisList2.append({'WEBSITE_ADDRESS': url})
            updateStat('ATTRIBUTE', 'WEBSITE_ADDRESS')
            
    if thisList1:
        jsonData['COMPANY_ADDRESS'] = thisList1
    if thisList2:
        jsonData['COMPANY_WEBSITE'] = thisList2
    if onlyCountryList: 
        jsonData['Address Country'] = ','.join(onlyCountryList)
            
    #--identifiers
    itemNum = 0
    thisList = []
    for idRecord in masterRecord.findall('IDNumberTypes/ID'):
        idType = idRecord.attrib['IDType']
        for idValue in idRecord.findall('IDValue'):
            idNumber = getValue(idValue)
            idNotes = getAttr(idValue, 'IDnotes')

            attrType1 = None
            attrType2 = None
            attrType3 = None
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
            elif idType.upper() == 'DUNS':
                attrType1 = 'DUNS_NUMBER'
            elif idType.upper() == 'OFAC UNIQUE ID':
                attrType1 = 'OFAC_ID'
            elif idType.upper() == 'NATIONAL PROVIDER IDENTIFIER (NPI)':
                attrType1 = 'NPI_NUMBER'
            elif idType.upper() == 'LEGAL ENTITY IDENTIFIER (LEI)':
                attrType1 = 'LEI_NUMBER'
            elif idType.upper() == 'NATIONAL CRIMINAL IDENTIFICATION CODE (USA)':
                attrType1 = 'NCIC_NUMBER'
            elif idType.upper() == 'CENTRAL REGISTRATION DEPOSITORY (CRD)':
                attrType1 = 'CRD_NUMBER'

            else:
                attrType1 = None

            #--if mapped
            if attrType1:

                #--parse notes for a country or state code
                isoCode = None
                if idNotes:

                    #--try for country code
                    if countryCheck:
                        isoCode = idNoteParse(idNotes, isoCountries)
                        if isoCode:
                            isoCountriesList.append(isoCode)

                    #--try for US state code
                    if countryCheck == 2 and (isoCode in ('USA', 'US') or not isoCode):
                        isoCode = idNoteParse(idNotes, isoStates)

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
            jsonData['ID%s' % itemNum] = idType + ' ' + idNumber + ((' ' + idNotes) if idNotes else '')
            
    if thisList:
        jsonData['IDENTIFIERS'] = thisList

    #--countries
    thisList = []
    for birthPlaceRecord in masterRecord.findall('BirthPlace/Place'):
        birthPlace = birthPlaceRecord.attrib['name']
        thisList.append({'PLACE_OF_BIRTH': birthPlace})
        updateStat('ATTRIBUTE', 'PLACE_OF_BIRTH')

        if birthPlace.lower() in isoCountries:
            #thisList.append({'POB_COUNTRY_CODE': isoCountries[birthPlace.lower()]})
            isoCountriesList.append(isoCountries[birthPlace.lower()])
        elif ',' in birthPlace:
            countryName = birthPlace[birthPlace.find(',')+1:].strip()
            if countryName.lower() in isoCountries: #--also map the code for matching
                #thisList.append({'POB_COUNTRY_CODE': isoCountries[countryName.lower()]})
                isoCountriesList.append(isoCountries[countryName.lower()])
            else:
                countryName = birthPlace[birthPlace.rfind(',')+1:].strip()
                if countryName.lower() in isoCountries: #--also map the code for matching
                    #thisList.append({'POB_COUNTRY_CODE': isoCountries[countryName.lower()]})
                    isoCountriesList.append(isoCountries[countryName.lower()])

    for countryRecord in masterRecord.findall('CountryDetails/Country'):
        countryType = countryRecord.attrib['CountryType']
        if countryType == 'Citizenship':
            featureCode = 'CITIZENSHIP'
        else:
            featureCode = None
        countryType = countryType.replace(' ','_')
        itemNum = 0
        for countryValue in countryRecord.findall('CountryValue'):
            countryCode = countryValue.attrib['Code']
            countryName = countryCodes[countryCode] if countryCode in countryCodes else countryCode
            if featureCode: 
                thisList.append({featureCode: countryName})
                updateStat('ATTRIBUTE', featureCode)
            else:
                jsonData[countryType + (('_' + str(itemNum)) if itemNum > 0 else '')] = countryName
                itemNum += 1
                updateStat('USEFUL_DATA', countryType)
            if countryName.lower() in isoCountries:
                isoCountriesList.append(isoCountries[countryName.lower()])

    if thisList:
        jsonData['COUNTRIES'] = thisList

    #--descriptions
    itemNum = 0
    for descriptionRecord in masterRecord.findall('Descriptions/Description'):
        try: description1 = description1Codes[descriptionRecord.attrib['Description1']]
        except: description1 = ''
        try: description2 = description2Codes[descriptionRecord.attrib['Description2']]
        except: description2 = ''
        try: description3 = description3Codes[descriptionRecord.attrib['Description3']]
        except: description3 = ''
        if description1 or description2 or description3:
            itemNum += 1
            description = description1
            description += (' | ' if description2 else '') + description2
            description += (' | ' if description3 else '') + description3
            jsonData["Description%s" % itemNum] = description
            updateStat('USEFUL_DATA', 'DESCRIPTIONS')

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
            updateStat('USEFUL_DATA', 'ROLES')

    #--references
    itemNum = 0
    for referenceRecord in masterRecord.findall('SanctionsReferences/Reference'):
        itemNum += 1
        referenceName = referenceCodes[getValue(referenceRecord)]
        jsonData["Reference%s" % itemNum] = referenceName
        updateStat('USEFUL_DATA', 'REFERENCES')
        
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
            relType = relationCodes[relationship['code']][0:25].replace(' ', '-')
            thisRecord = {}
            if noRelationships:
                thisRecord['Related to'] = '%s | %s | %s' % (dataSource, relationship['id'], relType[0:25])
            else:  
                relKey = '-'.join(sorted([thisId, relationship['id']]))
                thisRecord['RELATIONSHIP_ROLE'] = relType
                thisRecord['RELATIONSHIP_KEY'] = relKey
            updateStat('RELATIONSHIPS', relType)
            thisList.append(thisRecord)
            #--group association
            if recordType == 'PERSON' and relationship['id'] in entityNames:
                thisRecord = {}
                #thisRecord[relType + '_GROUP_ASSOCIATION_TYPE'] = 'ORG'
                thisRecord[relType + '_GROUP_ASSOCIATION_ORG_NAME'] = entityNames[relationship['id']]
                thisList.append(thisRecord)
                updateStat('GROUP_ASSOCIATIONS', relType)
    if thisList:
        jsonData['RELATIONSHIPS'] = thisList
        
    thisList = []
    for countryCode in set(isoCountriesList):
        thisList.append({'COUNTRY_CODE': countryCode})
        updateStat('ATTRIBUTE', 'COUNTRY_CODE')
    if thisList: 
        jsonData['ISO_COUNTRY_CODES'] = thisList

    #--create composite keys
    if False:
        ckDobList = set(ckDobList)
        ckCntryList = set(ckCntryList)
        ckCntryList = set(ckCntryList)
        ckYobList = set(ckYobList)
        if ckDobList or ckCntryList: 
            thisList = []

            for nameDict in jsonData['NAMES']:
                nameLast = nameDict['NAME_LAST'] if 'NAME_LAST' in nameDict else ''
                nameFull = nameDict['NAME_LAST'] if 'NAME_LAST' in nameDict else ''
                if 'NAME_FIRST' in nameDict and nameDict['NAME_FIRST']:
                    nameFull += ' ' + nameDict['NAME_FIRST']
                if 'NAME_MIDDLE' in nameDict and nameDict['NAME_MIDDLE']:
                    nameFull += ' ' + nameDict['NAME_MIDDLE']
                if not nameFull:
                    continue

                nameFullKey = '|'.join(sorted([x.upper() for x in nameFull.upper().replace('.',' ').replace(',',' ').split()]))
                nameLastKey = '|'.join(sorted([x.upper() for x in nameLast.upper().replace('.',' ').replace(',',' ').split()]))
                for dobKey in ckDobList:
                    thisList.append({"FF_NAME_DOB": nameFullKey + '|' + dobKey})
                    for cntryKey in ckCntryList:
                        thisList.append({"FF_NAME_DOB_CNTRY": nameFullKey + '|' + dobKey + '|' + cntryKey})
                        #thisList.append({"CK_LNAME_DOB_CNTRY": nameFullKey + '|' + dobKey + '|' + cntryKey})
                        #if nameLastKey:
                        #    thisList.append({"CK_LNAME_DOB_CNTRY": nameLastKey + '|' + dobKey + '|' + cntryKey})
                #for cntryKey in ckCntryList:
                    #thisList.append({"CK_NAME_CNTRY": nameFullKey + '|' + cntryKey})

            if thisList:
                jsonData['COMPOSITE_KEYS'] = thisList

    #if len(jsonData['IDENTIFIERS']) > 0:
    #    print jsonData['IDENTIFIERS']
    #    pause()
    
    #if jsonData['DATES']:
    #    print jsonData
    #    pause()

    return json.dumps(jsonData) + '\n'
        
#----------------------------------------
if __name__ == "__main__":
    appPath = os.path.dirname(os.path.abspath(sys.argv[0]))

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-i', '--inputFile', dest='inputFile', type=str, default=None, help='A Dow Jones xml file for PFA or HRF.')
    argparser.add_argument('-o', '--outputFile', dest='outputFile', type=str, help='output filename, defaults to input file name with a .json extension.')
    argparser.add_argument('-d', '--dataSource', dest='dataSource', type=str, help='please use DJ-PFA or DJ-HRF based on the type of file.')
    argparser.add_argument('-nr', '--noRelationships', dest='noRelationships', action='store_true', default = False, help='do not create disclosed realtionships, an attribute will still be stored')
    argparser.add_argument('-c', '--isoCountrySize', dest='isoCountrySize', type=int, default=3, help='ISO country code size. Either 2 or 3, default=3.')
    argparser.add_argument('-s', '--statisticsFile', dest='statisticsFile', type=str, help='optional statistics filename in json format.')
    args = argparser.parse_args()
    inputFile = args.inputFile
    outputFile = args.outputFile
    dataSource = args.dataSource
    noRelationships = args.noRelationships
    isoCountrySize = args.isoCountrySize
    statisticsFile = args.statisticsFile
    
    if not dataSource and 'PFA' in inputFile.upper():
        dataSource = 'DJ-PFA'
    elif not dataSource and 'HRF' in inputFile.upper():
        dataSource = 'DJ-HRF'

    if not dataSource or dataSource.upper() not in ('DJ-PFA', 'DJ-HRF'):
        print('')
        print('must specify either DJ-PFA or DJ-HRF as the data source with -d')
        print('')
        sys.exit(1)
    else:
        dataSource = dataSource.upper()
        
    if not inputFile:
        print('')
        print('must select a dow jones xml input file with -i')
        print('')
        sys.exit(1)

    if not os.path.exists(inputFile):
        print('')
        print('input file %s not found!' % inputFile)
        print('')
        sys.exit(1)
    
    if not (outputFile):
        outputFile = inputFile + '.json'

    #--initialize some stats
    recordCnt = 0
    personCnt = 0
    entityCnt = 0
    statPack = {}
    longNameOrgCnt = 0
    longNameLastCnt = 0
    longNameMaidenCnt = 0
    longNameFirstCnt = 0
    longNameMiddleCnt = 0
    longAddrLineCnt = 0
    
    #--need month conversions
    monthNum = {}
    monthNum['JAN'] = '01'
    monthNum['FEB'] = '02'
    monthNum['MAR'] = '03'
    monthNum['APR'] = '04'
    monthNum['MAY'] = '05'
    monthNum['JUN'] = '06'
    monthNum['JUL'] = '07'
    monthNum['AUG'] = '08'
    monthNum['SEP'] = '09'
    monthNum['OCT'] = '10'
    monthNum['NOV'] = '11'
    monthNum['DEC'] = '12'
            
    #--need conversion table for country codes
    if isoCountrySize == 3:
        isoCountryFile = 'isoCountries3.json'
    elif isoCountrySize == 2:
        isoCountryFile = 'isoCountries2.json'
    else:
        print('')
        print('The ISO Country size must be 2 or 3.')
        print('')
        sys.exit(1)
    isoCountryFile = appPath + os.path.sep + isoCountryFile
    if not os.path.exists(isoCountryFile):
        print('')
        print('File %s is missing!' % (isoCountryFile))
        print('')
        sys.exit(1)
    try: isoCountries = json.load(open(isoCountryFile,'r'))
    except json.decoder.JSONDecodeError as err:
        print('')
        print('JSON error %s in %s' % (err, isoCountryFile))
        print('')
        sys.exit(1)
    isoStatesFile = appPath + os.path.sep + 'isoStates.json'
    if not os.path.exists(isoStatesFile):
        print('')
        print('File %s is missing!' % (isoCountriesFile))
        print('')
        sys.exit(1)
    try: isoStates = json.load(open(isoStatesFile,'r'))
    except json.decoder.JSONDecodeError as err:
        print('')
        print('JSON error %s in %s' % (err, isoStatesFile))
        print('')
        sys.exit(1)

    #--initialize code dictionaries
    countryCodes = {}
    description1Codes = {}
    description2Codes = {}
    description3Codes = {}
    referenceCodes = {}
    relationCodes = {}
    relationships = {}
    entityNames = {}

    #--iterate through the xml file serially as it is huge! 
    print('')
    print('Data source set to %s' % dataSource)
    print('')
    print('Reading from: %s ...' % inputFile)
    xmlReader = etree.iterparse(inputFile, events=("start", "end"))
    for event, node in xmlReader:
        if event == 'end':

            if node.tag == 'CountryList':
                print('loading %s ...' % node.tag) 
                notfound = 0
                found = 0
                for record in node.findall('CountryName'):
                    countryCodes[getAttr(record, 'code')] = getAttr(record, 'name')
                    if not getAttr(record, 'name').lower() in isoCountries:
                        #print(getAttr(record, 'name'))
                        notfound += 1
                    else:
                        found += 1
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
    
    #--open the output file
    outputHandle = open(outputFile, "w", encoding='utf-8')

    #--go through a second time to process the records
    print('')
    print('processing records ...')
    xmlReader = etree.iterparse(inputFile, events=("start", "end"))
    for event, node in xmlReader:
        if event == 'end' and node.tag in ('Person','Entity'):
            if node.tag == 'Person':
                outputHandle.write(g2Mapping(node, 'PERSON'))
                personCnt += 1 
            else:
                outputHandle.write(g2Mapping(node, 'ORGANIZATION'))
                entityCnt += 1
                
            node.clear()
            recordCnt += 1 
            if recordCnt % 10000 == 0:
                print('%s rows processed' % recordCnt)
        
    outputHandle.close()
    
    print('%s rows processed, completed!' % recordCnt)
    print('%s persons' % personCnt)
    print('%s entities' % entityCnt)
    print('%s longNameOrgCnt' % longNameOrgCnt)
    print('%s longNameLastCnt' % longNameLastCnt)
    print('%s longNameMaidenCnt' % longNameMaidenCnt)
    print('%s longNameFirstCnt' % longNameFirstCnt)
    print('%s longNameMiddleCnt' % longNameMiddleCnt)
    print('%s longAddrLineCnt' % longAddrLineCnt)
    print('')
    if statisticsFile: 
        with open(statisticsFile, 'w') as outfile:
            json.dump(statPack, outfile, indent=4, sort_keys=True)    
        print('Mapping stats written to %s' % statisticsFile)
        print('')
    
    sys.exit(0)
   
