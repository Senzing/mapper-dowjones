# mapper-dowjones

## Overview

The [dj2json.py](dj2json.py) python script converts Dow Jones Watch list files to json files ready to load into senzing.  This includes their ...
- Risk and Compliance database (PFA) 
- High Risk File or (HRF)

If you subscribe to the either Dow Jones Risk and Compliance database, you will have instructions from them on how to login and download monthly or daily files.  When looking at the files on-line, there are monthly full files and daily updates. The idea is that you periodically refresh their full file and perform daily updates on top of it.

Loading watch lists requires some special features and configurations of Senzing. These are contained in the 
[djConfigUpdates.json](djConfigUpdates.json) file and are applied with the [G2ConfigTool.py](G2ConfigTool.py) contained in this project.

**IMPORTANT NOTE:** For good watch list matching, your other data sources should also map as many these same features as are available!  

Usage:
```console
usage: dj2json.py [-h] [-i INPUTFILE] [-o OUTPUTFILE] [-d DATASOURCE]
                  [-r DISCRELTYPE] [-c ISOCOUNTRYSIZE] [-s STATISTICSFILE]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUTFILE, --inputFile INPUTFILE
                        A Dow Jones xml file for PFA or HRF.
  -o OUTPUTFILE, --outputFile OUTPUTFILE
                        output filename, defaults to input file name with a
                        .json extension.
  -d DATASOURCE, --dataSource DATASOURCE
                        please use DJ-PFA or DJ-HRF based on the type of file.
  -r DISCRELTYPE, --discrelType DISCRELTYPE
                        disclosed relationship type (1-standard, 2=pointer
                        only, 0=none)
  -c ISOCOUNTRYSIZE, --isoCountrySize ISOCOUNTRYSIZE
                        ISO country code size. Either 2 or 3, default=3.
  -s STATISTICSFILE, --statisticsFile STATISTICSFILE
                        optional statistics filename in json format.
```

## Contents

1. [Prerequisites](#Prerequisites)
2. [Installation](#Installation)
3. [Configuring Senzing](#Configuring-Senzing)
4. [Running the dj2json mapper](#Running-the-dj2json-mapper)
5. [Loading into Senzing](#Loading-into-Senzing)
6. [Mapping other data sources](#Mapping-other-data-sources)
7. [Optional ini file parameter](#Optional-ini-file-parameter)

### Prerequisites
- python 3.6 or higher
- Senzing API version 1.7 or higher

### Installation

Place the the following files on a directory of your choice ...
- [dj2json.py](dj2json.py) 
- [djConfigUpdates.json](djConfigUpdates.json)
- [isoCountries2.json](isoCountries2.json)
- [isoCountries3.json](isoCountries3.json)
- [isoStates.json](isoStates.json)

*Note:* The iso\*.json file are extensible. They currently only contain the most common country and state name variations. Additional entries can be added as desired. This conversion program extracts and standardizes country codes from the fields: nationality, citizenship, place of birth, addresses, passports and other national identifiers and places them into a standardized country code attribute very useful for matching. *For best results, you will want to use these files to help standardize country and state codes from these fields in your other data sources as well.*

### Configuring Senzing

*Note:* This only needs to be performed one time! In fact you may want to add these configuration updates to a master configuration file for all your data sources.

Update the G2ConfigTool.py program file on the /opt/senzing/g2/python directory with this one ... [G2ConfigTool.py](G2ConfigTool.py)

Then from the /opt/senzing/g2/python directory ...
```console
python3 G2ConfigTool.py <path-to-file>/djConfigUpdates.json
```
This will step you through the process of adding the data sources, entity types, features, attributes and other settings needed to load this watch list data into Senzing. After each command you will see a status message saying "success" or "already exists".  For instance, if you run the script twice, the second time through they will all say "already exists" which is OK.

Configuration updates include:
- addDataSource **DJ-PFA**
- addDataSource **DJ-HRF**
- addEntityType **PERSON**
- addEntityType **ORGANIZATION**
- add features and attributes for ...
    - **RECORD_TYPE** This helps keep persons and organizations from resolving together.
    - **COUNTRY_CODE** This is a 3 character country code used to improve matching of nationality, citizenship and place of birth.
    - **PLACE_OF_BIRTH** This is a feature missing from the default configuration of early versions of Senzing
    - **DATE_OF_DEATH** This is a feature missing from the default configuration of early versions of Senzing
    - **DJ_PROFILE_ID** This is used to help prevent watch list entries from resolving to each other and so that you can search on it.
    - **OFAC_ID** This is used to help prevent watch list entries from resolving to each other and so that you can search on it.
    - **DUNS_NUMBER** This is globally unique identifier issued to companies by Dun and Bradstreet.
    - **LEI_NUMBER** This is a globally unique identifier of legal entities participating in financial transactions. These can be individuals, companies or government entities.
    - **CRD_NUMBER** This is a unique identifier assigned by FINRA for all firms and individuals involved in the U.S. securities industry.
    - **COMPANY_ID** It is unclear from Dow Jones documentation exactly what this number is, but it appears to be a registry of companies by country.
    - **NPI_NUMBER** This is a unique identifier for covered health care providers. 
    - **NCIC_NUMBER** This is a unique identifier for an entry in the FBI's National Crime Information Center. 
- Year of birth and country codes are added to the name hasher elements for composite keys.

*WARNING:* the following settings are commented out as they affect performance and quality. Only use them if you understand and are OK with the effects.
- sets **NAME** and **ADDRESS** to be used for candidates. Normally just their hashes are used to find candidates.  The effect is performance is slightly degraded.
- set **GROUP_ASSOCIATION** feature to be used for candidates.

- set **distinct** off.  Normally this is on to prevent lower strength AKAs to cause matches as only the most distinct names are considered. The effect is more potential false positives.

### Running the dj2json mapper

First, download the xml file you want to load from the DowJones website.  Here are a couple of examples of how the files will be named ...
- PFA2_201902282200_F.xml           <--Risk and Compliance database (PFA)
- DJRC_HRF_XML_201903012359_F.xml   <--High Risk File or (HRF) 
It would be a good practice to keep a history of these files on a directory where you will store other source data files loaded into Senzing. 

Second, run the mapper.  Typical usage:
```console
python3 dj2json.py -i /<path-to-file>/PFA2_201902282200_F.xml
```
The output file defaults to the same name and location as the input file and a .json extension is added.
- Use the -o parameter if you want a supply a different output file name or location
- Use the -c parameter to change from 3 character to 2 character ISO country codes.
- use the -d parameter if you have renamed the input file so that neither PFA nor HRF is in the file name.
- Use the -s parameter to log the mapping statistics to a file.

*Note* The mapping satistics should be reviewed occasionally to determine if there are other values that can be mapped to new features.  Check the UNKNOWN_ID section for values that you may get from other data sources that you would like to make into their own features.  Most of these values were not mapped because there just aren't enough of them to matter and/or you are not likely to get them from any other data sources. However, DUNS_NUMBER, LEI_NUMBER, and the new features added were found by reviewing these statistics!

### Loading into Senzing

If you use the G2Loader program to load your data, from the /opt/senzing/g2/python directory ...
```console
python3 G2Loader.py -f /<path-to-file>/PFA2_201902282200_F.xml.json
```
The PFA data set currently contains about 2.4 million records and make take a few hours to load depending on your harware.  The HRF file only contains about 70k records and loads in a few minutes. 

If you use the API directly, then you just need to perform an addRecord for each line of the file.

### Mapping other data sources

Watch lists are harder to match simply because often the only data they contain that matches your other data sources are name, partial date of birth, and citizenship or nationality.  Complete address or identifier matches are possible but more rare. For this reason, the following special attributes should be mapped from your internal data sources or search request messages ... 
- **RECORD_TYPE** (valid values are PERSON or ORGANIZATION, only supply if known.)
- **COUNTRY_CODE** (standardized with [isoCountries.json](isoCountries.json)) Simply find any country you can that qualifies as a nationality, citizenship or place of birth, find it in the isCountries file and map the iso3 value as COUNTRY_CODE. 
- **GROUP_ASSOCIATION_ORG_NAME** (Sometimes all you know about a person is who they work for or what groups they are otherwise affiliated with. Consider a contact list that has name, phone number, and company they work for.   Map the company name to the GROUP_ASSOCIATION_ORG_NAME attribute as that may be the only matching attribute to the watch list.

### Optional ini file parameter

There is also an ini file change that can benefit watch list matching.  In the pipeline section of the main g2 ini file you use, such as the /opt/senzing/g2/python/G2Module.ini, place the following entry in the pipeline section as show below.

```console
[pipeline]
 NAME_EFEAT_WATCHLIST_MODE=Y
```

This effectively doubles the number of name hashes created which improves the chances of finding a match at the cost of performance.  Consider creating a separate g2 ini file used just for searching and include this parameter.  If you include it during the loading of data, only have it on while loading the watch list as the load time will actually more than double! 

