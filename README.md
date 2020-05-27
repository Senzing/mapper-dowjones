# mapper-dowjones

## Overview

The [dj_mapper.py](dj_mapper.py) python script converts Dow Jones Watch list files to json files ready to load into Senzing.  This includes the following databases ...

- Risk and Compliance database (PFA)
- High Risk File or (HRF)
- Adverse Media Entities (AME)

If you subscribe to the either Dow Jones Risk and Compliance database, you will have instructions from them on how to login and download monthly or daily files.  The idea is that you periodically refresh their full file and perform daily updates on top of it.

Loading Dow Jones data into Senzing requires additional features and configurations. These are contained in the
[dj_config_updates.json](dj_config_updates.json) file.

Usage:

```console
python dj_mapper.py --help
usage: dj_mapper.py [-h] [-i INPUT_FILE] [-o OUTPUT_FILE] [-l LOG_FILE]
                    [-d DATA_SOURCE] [-r RELATIONSHIP_STYLE] [-e]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input_file INPUT_FILE
                        A Dow Jones xml file for PFA or HRF.
  -o OUTPUT_FILE, --output_file OUTPUT_FILE
                        output filename, defaults to input file name with a
                        .json extension.
  -l LOG_FILE, --log_file LOG_FILE
                        optional statistics filename (json format).
  -d DATA_SOURCE, --data_source DATA_SOURCE
                        please use DJ-PFA, DJ-HRF or DJ-AME based on the type of file.
  -r RELATIONSHIP_STYLE, --relationship_style RELATIONSHIP_STYLE
                        styles: 0=None, 1=Legacy linking, 2=Pointers (new for
                        Senzing v1.15)
  -e, --extended_format
                        include profile notes, sources, and images
```

## Contents

1. [Prerequisites](#prerequisites)
1. [Installation](#installation)
1. [Configuring Senzing](#configuring-senzing)
1. [Running the mapper](#running-the-mapper)
1. [Loading into Senzing](#loading-into-senzing)
1. [Mapping other data sources](#mapping-other-data-sources)

### Prerequisites

- python 3.6 or higher
- Senzing API version 1.13 or higher
- [Senzing/mapper-base](https://github.com/Senzing/mapper-base)

### Installation

Place the the following files on a directory of your choice ...

- [dj_mapper.py](dj_mapper.py)
- [dj_config_updates.json](dj_config_updates.json)

*Note: Since the mapper-base project referenced above is required by this mapper, it is necessary to place them in a common directory structure like so ...*

```Console
/senzing/mappers/mapper-base
/senzing/mappers/mapper-dowjones  <--
```

You will also need to set the PYTHONPATH to where the base mapper is as follows ... (assumuing the directory structure above)

```Console
export PYTHONPATH=$PYTHONPATH:/senzing/mappers/mapper-base
```

### Configuring Senzing

*Note:* This only needs to be performed one time! In fact you may want to add these configuration updates to a master configuration file for all your data sources.

From the /opt/senzing/g2/python directory ...

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
  - **DJ_PROFILE_ID** This is used to help prevent watch list entries from resolving to each other and so that you can search on it.
  - **OFAC_ID** This is used to help prevent watch list entries from resolving to each other and so that you can search on it.
  - **NCIC_NUMBER** This is a unique identifier for an entry in the FBI's National Crime Information Center.
  - **CRD_NUMBER** This is a unique identifier assigned by FINRA for all firms and individuals involved in the U.S. securities industry.
  - **COMPANY_ID** It is unclear from Dow Jones documentation exactly what this number is, but it appears to be a registry of companies by country.

### Running the mapper

First, download the xml file you want to load from the DowJones website.  Here are a couple of examples of how the files will be named ...

- PFA2_201902282200_F.xml           <--Risk and Compliance database (PFA)
- DJRC_HRF_XML_201903012359_F.xml   <--High Risk File or (HRF)

It is good practice to keep a history of these files on a directory where you will store other source data files loaded into Senzing.

Second, run the mapper. Example usage:

```console
python3 dj_mapper.py -i ./input/PFA2_201303312200_F.xml -o ./output/PFA2_201303312200_F.json -l pfa_stats.json
```

The output file defaults to the same name and location as the input file and a .json extension is added.

- Add the -d parameter if you have renamed the input file so that neither PFA nor HRF is in the file name.

- Add the -e parameter if you want to include the following fields: profile notes, sources, and images.

- Add the -r 1 parameter if you are on Senzing versions prior to v1.15.

*Note* The log file should be reviewed occasionally to determine if there are other values that can be mapped to new features.  Check the "UNKNOWN" section for values that you may get from other data sources that you would like to make into features.  Most of these values were not mapped because there just aren't enough of them to matter and/or you are not likely to get them from any other data sources. However, DUNS_NUMBER, LEI_NUMBER, and the other new features listed above were found by reviewing these statistics!

### Loading into Senzing

If you use the G2Loader program to load your data, from the /opt/senzing/g2/python directory ...

```console
python3 G2Loader.py -f /mapper_dowjones/output/PFA2_201902282200_F.json
```

The PFA data set currently contains about 2.4 million records and make take a few hours to load depending on your harware.  The HRF data set only contains about 70k records and loads in a few minutes.

If you use the API directly, then you just need to perform an process() or addRecord() for each line of the file.

### Mapping other data sources

Watch lists are harder to match simply because often the only data they contain that matches your other data sources are name, partial date of birth, and citizenship or nationality.  Complete address or identifier matches are possible but more rare. Likewise, employer names and other group affiliations can also help match watch lists.  Look for and map these features in your source data ...

- CITIZENSHIP
- NATIONALITY
- ADDRESS_COUNTRY in addresses
- PASSPORT_COUNTRY and other identifier countries
- GROUP_ASSOCIATION_ORG_NAME (employers and other group affiliations)
