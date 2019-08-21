# mapper-dowjones

## Overview

The [dj2json.py](dj2json.py) python script converts Dow Jones Watch list files to json files ready to load into senzing.  This includes their ...
- Risk and Compliance database (PFA) 
- High Risk File or (HRF)

If you subscribe to the either Dow Jones Risk and Compliance database, you will have instructions from them on how to login and download monthly or daily files.  The idea is that you periodically refresh their full file and perform daily updates on top of it.

Loading Dow Jones data into Senzing requires additional features and configurations. These are contained in the 
[djConfigUpdates.json](djConfigUpdates.json) file and are applied with the [G2ConfigTool.py](G2ConfigTool.py) contained in this project.

Usage:
```console
python dj_mapper.py --help
usage: dj_mapper.py [-h] [-m MAPPING_LIBRARY_PATH] [-i INPUT_FILE]
                    [-o OUTPUT_FILE] [-d DATA_SOURCE] [-c ISO_COUNTRY_SIZE]
                    [-s STATISTICS_FILE] [-nr]

optional arguments:
  -h, --help            show this help message and exit
  -m MAPPING_LIBRARY_PATH, --mapping_library_path MAPPING_LIBRARY_PATH
                        path to the mapping functions library files.
  -i INPUT_FILE, --input_file INPUT_FILE
                        A Dow Jones xml file for PFA or HRF.
  -o OUTPUT_FILE, --output_file OUTPUT_FILE
                        output filename, defaults to input file name with a
                        .json extension.
  -d DATA_SOURCE, --data_source DATA_SOURCE
                        please use DJ-PFA or DJ-HRF based on the type of file.
  -c ISO_COUNTRY_SIZE, --iso_country_size ISO_COUNTRY_SIZE
                        ISO country code size. Either 2 or 3, default=3.
  -s STATISTICS_FILE, --statistics_file STATISTICS_FILE
                        optional statistics filename in json format.
  -nr, --no_relationships
                        do not create disclosed realtionships, an attribute
                        will still be stored
```

## Contents

1. [Prerequisites](#Prerequisites)
2. [Installation](#Installation)
3. [Configuring Senzing](#Configuring-Senzing)
4. [Running the mapper](#Running-the-mapper)
5. [Loading into Senzing](#Loading-into-Senzing)
6. [Mapping other data sources](#Mapping-other-data-sources)
7. [Optional ini file parameter](#Optional-ini-file-parameter)

### Prerequisites
- python 3.6 or higher
- Senzing API version 1.7 or higher
- https://github.com/Senzing/mapper-functions

### Installation

Place the the following files on a directory of your choice ...
- [dj_mapper.py](dj_mapper.py)
- [dj_config_updates.json](dj_config_updates.json)

*Note: Since the mapper-functions project referenced above is required by this mapper, it is necessary to place them in a common directory structure.*

### Configuring Senzing

*Note:* This only needs to be performed one time! In fact you may want to add these configuration updates to a master configuration file for all your data sources.

Update the G2ConfigTool.py program file on the /opt/senzing/g2/python directory with this one ... [G2ConfigTool.py](G2ConfigTool.py)

Then from the /opt/senzing/g2/python directory ...
```console
python3 G2ConfigTool.py <path-to-file>/dj_config_updates.json
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
- Group association type is defaulted to (org) so it does not have to be mapped and will be the same across data sources.
- The following composite keys are added ...
    - CK_NAME_DOB_CNTRY
    - CK_NAME_DOB
    - CK_NAME_CNTRY
    - CK_NAME_ORGNAME

*WARNING:* the following settings are commented out as they affect performance and quality. Only use them if you understand and are OK with the effects.
- sets **NAME** and **ADDRESS** to be used for candidates. Normally just their hashes are used to find candidates.  The effect is performance is slightly degraded.
- set **GROUP_ASSOCIATION** feature to be used for candidates.

- set **distinct** off.  Normally this is on to prevent lower strength AKAs to cause matches as only the most distinct names are considered. The effect is more potential false positives.

### Running the mapper

First, download the xml file you want to load from the DowJones website.  Here are a couple of examples of how the files will be named ...
- PFA2_201902282200_F.xml           <--Risk and Compliance database (PFA)
- DJRC_HRF_XML_201903012359_F.xml   <--High Risk File or (HRF) 

It is good practice to keep a history of these files on a directory where you will store other source data files loaded into Senzing. 

Second, run the mapper. Example usage:
```console
python3 dj_mapper.py -m ../mapper-functions -i ./input/PFA2_201303312200_F.xml -o ./output/PFA2_201303312200_F.json
```
The output file defaults to the same name and location as the input file and a .json extension is added.
- Add the -c parameter to change from 3 character to 2 character ISO country codes.
- Add the -d parameter if you have renamed the input file so that neither PFA nor HRF is in the file name.
- Add the -s parameter to log the mapping statistics to a file.
- Add the -nr parameter to not create relationships.  This watch list has many disclosed relationships.  It is good to have them, but it loads faster if you turn them off.

*Note* The mapping satistics should be reviewed occasionally to determine if there are other values that can be mapped to new features.  Check the UNKNOWN_ID section for values that you may get from other data sources that you would like to make into features.  Most of these values were not mapped because there just aren't enough of them to matter and/or you are not likely to get them from any other data sources. However, DUNS_NUMBER, LEI_NUMBER, and the other new features listed above were found by reviewing these statistics!

### Loading into Senzing

If you use the G2Loader program to load your data, from the /opt/senzing/g2/python directory ...
```console
python3 G2Loader.py -f /mapper_dowjones/output/PFA2_201902282200_F.json
```
The PFA data set currently contains about 2.4 million records and make take a few hours to load depending on your harware.  The HRF data set only contains about 70k records and loads in a few minutes. 

If you use the API directly, then you just need to perform an process() or addRecord() for each line of the file.

### Mapping other data sources

Watch lists are harder to match simply because often the only data they contain that matches your other data sources are name, partial date of birth, and citizenship or nationality.  Complete address or identifier matches are possible but more rare. For this reason, the following special attributes should be mapped from your internal data sources or search request messages ... 
- **RECORD_TYPE** (valid values are PERSON or ORGANIZATION, only supply if known.)
- **COUNTRY_CODE:** standardized country codes using the mapping_functions project. Simply find any country in your source data and look it up in mapping_standards.json file and map its iso code to an attribute called country_code. You can prefix with a source word like so ...
```console
{
  "NATIONALITY_COUNTRY_CODE": "GER",
  "CITIZENSHIP_COUNTRY_CODE": "USA",
  "PLACE-OF-BIRTH_COUNTRY_CODE": "USA",     <--note the use of dashes not underscores here!
  "ADDRESS_COUNTRY_CODE": "CAN"},
  "PASSPORT_COUNTRY_CODE": "GER"}
}
```
*note: if your source word is an expression, use dashes not underscores so as not to confuse the engine*
- **GROUP_ASSOCIATION_ORG_NAME** (Sometimes all you know about a person is who they work for or what groups they are affiliated with. Consider a contact list that has name, phone number, and company they work for.   Map the company they work for to the GROUP_ASSOCIATION_ORG_NAME attribute as that may be the only matching attribute to the watch list.
- **PLACE_OF_BIRTH**, **DUNS_NUMBER**, or any of the other additional features listed above. 

### Optional ini file parameter

There is also an ini file change that can benefit watch list matching.  In the pipeline section of the main g2 ini file you use, such as the /opt/senzing/g2/python/G2Module.ini, place the following entry in the pipeline section as show below.

```console
[pipeline]
 NAME_EFEAT_WATCHLIST_MODE=Y
```

This effectively doubles the number of name hashes created which improves the chances of finding a match at the cost of performance.  Consider creating a separate g2 ini file used just for searching and include this parameter.  If you include it during the loading of data, only have it on while loading the watch list as the load time will actually more than double! 

