# Redfish Schema Creator

Copyright 2020 DMTF. All rights reserved.

## About

The most efficient method of crafting a new schema has been to first create a mockup of the data as a JSON payload.  Once the data makes sense in that form, sometimes with the addition of a property description list, a schema is then prepared.

This utility will read a JSON document and using the Redfish conventions and some optional annotations, output a "mostly complete" CSDL Redfish schema file.  In addition, as typing the Description and LongDescription text can be cumbersome within a CSDL document, and may have been written in a spreadsheet or other tool prior to schema creation, the utility will also merge a CSV file to incorporate description text into the schema output.


## Usage

```
usage: csdl_creator.py [-h] [--desc DESC] [--csv CSV] [--toggle] json

Builds a mostly complete CSDL file from an annotated JSON file and an optional
CSV file.

positional arguments:
  json         file to process

optional arguments:
  -h, --help   show this help message and exit
  --desc DESC  sysdescription for identifying logs
  --csv CSV    csv file of helpful definitions for this file
  --toggle     print a csv report at the end of the log
```

## JSON document

The input document must be valid JSON.  The following schema attributes will be determined directly from the JSON payload:
* Schema name (value of @odata.type)
* Property names
* Data types (string, integer, number/float, boolean)
* Array definitions (item type from data type)
* Enum values - string with "|" separators between enum values e.g. "On | Off | Blinking"
* Embedded object hierarchy 
* Links objects and navigation properties (object with @odata.id property)
* Actions definitions from Actions object
* References to properties in Resource_v1 can be detected and referenced
* If annotated, include schema reference for any links


### Annotations

The addition of property-level annotations aid in completing the schema creation. An annotation is constructed using the property name with a "!" separator and annotation name appended.  Defined annotations include:
* <property>!description - Description text
* <property>!longDescription - Long Description text
* <property>!link - Schema name for link target (populate property and schema reference)
* <property>!readonly - mark property as R/W instead of R/O (default is R/O)
* <property>!required - mark property as Required


### Sample annotated JSON

```json
{
    "@odata.id": "/redfish/v1/Thingy/1",
    "@odata.type": "#Thingy.v1_0_0.Thingy",
    "Id": "1",
    "Name": "Big Thingy",
    "ThingType": "RackMount | Cheap | Expensive | Obsolete | Trendy",
	"ThingType!required": true,
	"ThingType!description": "The type of thingy that this thingy is - really...",
    "IndicatorLED": "Off | Lit | Blinking",
	"IndicatorLED!readonly": false,
    "Location": { },
    "Status": {
        "State": "Enabled",
        "Health": "OK"
    },
    "PCIeSlots": {
        "@odata.id": "/redfish/v1/Chassis/1/PCIeSlots"
    },
	"PCIeSlots!link": "PCIeDevice",
    "Thermal": {
        "@odata.id": "/redfish/v1/Chassis/1/Thermal"
    },
	"Thermal!link": "Thermal",
    "Power": {
        "@odata.id": "/redfish/v1/Chassis/1/Power"
    }
}
```

## Supplemental CSV file

A comma-separated variable (CSV) file can be specified as input to provide description text, using the following:

`<property name>, <description>, <long description>`

The property name could also provide a JSON path `object/property` or similar style to allow inclusion of properties within embedded objects.


## XML header file

An XML file with the default comment block header, follow existing Redfish schema, with keyword for schema name replacement.


## Schema output

The utility will process the JSON document and CSV file, if provided, to produce a Redfish CSDL schema file with incomplete data notated for user to provide, and reasonable defaults taken for other attributes that cannot be determined.

Default property attributes:
* Properties marked as read-only
* Properties non-nullable
* Schema version and namespace is v1.0.0

Default inclusions:
* Actions block
* Capabilities block
* OEM block

Default text:
* "***TBD***" strings for Description and LongDescription text if not found in payload or CSV
* "***TBD***" names for linked schemas and types if not provided in annotations.
* Generic description/longDescription for links based on existing Redfish style
