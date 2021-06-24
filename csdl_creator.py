# Copyright Notice:
# Copyright 2017-2020 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Schema-Creator/blob/master/LICENSE.md

import re
import sys
import csv
import json
import argparse
import lxml
import xml_convenience
import xml.dom.minidom
import xml.etree.ElementTree as etree
# from xml.etree.ElementTree import Element, SubElement, Comment, tostring

REGEX_TYPE = "#([a-zA-z]*.v\\d_\\d_\\d)"

RESOURCE_TYPES = ['Id', 'Description', 'Name', 'UUID', 'Links', 'Oem', 'OemObject', 'ItemOrCollection', 'Item', 'ReferenceableMember', 'Resource', 'ResourceCollection', 'Status', 'State', 'Health', 'ResetType', 'Identifier', 'Location', 'IndicatorLED', 'PowerState']

RESOURCE_PROPERTIES = ['Description', 'Name', 'Id']

RESOURCE_COLLECTION_PROPERTIES = ['Description', 'Name', 'Oem']

CSDL_HEADER_TEMPLATE = """<!---->
<!--################################################################################       -->
<!--# Redfish Schema:  {}                                          -->
<!--#                                                                                      -->
<!--# For a detailed change log, see the README file contained in the DSP8010 bundle,      -->
<!--# available at http://www.dmtf.org/standards/redfish                                   -->
<!--# Copyright 2020 DMTF.                                                                 -->
<!--# For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright -->
<!--################################################################################       -->
<!---->
"""

def database_builder(annotated_json, csv={}):
    """Transforms annotated json into a dictionary database
    
    :param annotated_json: Annotated json to turn into a dictionary.
    :type annotated_json: dict
    :param data_base: The dictionary containing the final database. Pass this as an empty dict.
    :type data_base: dict
    """
    data_base = {}
    for key, value in annotated_json.items():
        # Use ! to delineate Schema Annotation
        if '!' in key:
            prop, annotation = tuple(key.split('!', 1))
        else:
            prop, annotation = key, None
        # Skip all @ items
        if '@' in key or prop in ['', None]:
            continue
        data_base[prop] = {} if prop not in data_base else data_base[prop]
        if annotation is None:
            if isinstance(value, list):
                data_base[prop]["items"] = {
                    "type": list(set([type(x) for x in value]))
                }
                data_base[prop]["type"] = "array"
                value = value[0]
            if isinstance(value, dict):
                sub_csv = {k.split('/', 1)[1]: s for k, s in csv.items() if prop in k and '/' in k}
                data_base[prop]["properties"] = database_builder(value, sub_csv)
            elif isinstance(value, str) and '|' in value:
                #For enum values
                value = [val.strip() for val in value.split('|') if val]
                data_base[prop]["enum"] = True
            data_base[prop]["value"] = value
        else:
            data_base[prop][annotation] = value
    for prop in data_base:
        if prop in csv:
            print(prop)
            data_base[prop]['description'] = csv[prop][0]
            data_base[prop]['longDescription'] = csv[prop][1]
            if data_base[prop].get("enum"):
                csv_enum = csv[prop][2:]
                print(csv_enum, prop)
                if data_base[prop].get("enumDescriptions") is None:
                    data_base[prop]["enumDescriptions"] = {}
                data_base[prop]["enumDescriptions"].update({e: d for e, d in zip(data_base[prop]["value"], csv_enum)})


    return data_base


def create_navigation(property_name, schema_name="TBD", description=None, longDescription=None, collection=False, **kwargs):
    """Creates a navigation entry to add to the CSDL schema."""
    description = description if description else "A link to {}".format(property_name)
    longDescription = longDescription if longDescription else "This property shall be a link to a resource collection of type {}.".format(property_name)

    if collection:
        navegation_entry = etree.Element("NavigationProperty",\
            attrib={"Name": property_name, "Type": "Collection({}.{})".format(schema_name, schema_name), "Nullable": "false"})
    else:
        navegation_entry = etree.Element("NavigationProperty",\
            attrib={"Name": property_name, "Type": "{}.{}".format(schema_name, schema_name), "Nullable": "false"})

    etree.SubElement(navegation_entry, "Annotation", 
        attrib={"Term":"OData.Permissions", "EnumMember": "OData.Permission/Read"} )
    etree.SubElement(navegation_entry, "Annotation", attrib={"Term": "OData.Description", "String": description})
    etree.SubElement(navegation_entry, "Annotation", attrib={"Term": "OData.LongDescription", "String": longDescription})
    if collection:
        etree.SubElement(navegation_entry, "Annotation", {'Term':'OData.AutoExpandReferences'})

    return navegation_entry


def create_property(property_name, property_type, readonly=True, required=False, type=None, description=None, longDescription=None, items=None):
    """Creates a base property to build from"""
    description = description if description else "TBD"
    longDescription = longDescription if longDescription else "TBD"
    readonly = "OData.Permission/Read" if readonly else "OData.Permission/ReadWrite"

    property_string = "ComplexType" if complex else "Property"

    added_property = etree.Element("Property", attrib={"Name": property_name, "Type": property_type, "Nullable": "false"})
    etree.SubElement(added_property, "Annotation", attrib={"Term": "OData.Permissions", "EnumMember": readonly})
    etree.SubElement(added_property, "Annotation", attrib={"Term": "OData.Description", "String": description})
    etree.SubElement(added_property, "Annotation", attrib={"Term": "OData.LongDescription", "String": longDescription})
    if required:
        etree.SubElement(added_property, "Annotation", attrib={"Term": "Redfish.Required"})

    return added_property

    
def create_complex_property(property_name, base_type=None, description=None, longDescription=None, readonly=True, type=None, **kwargs):
    """Create a complex property type"""
    description = description if description else "TBD"
    longDescription = longDescription if longDescription else "TBD"
    added_property = etree.Element("ComplexType", attrib={"Name": property_name, "Nullable": "false"})
    if base_type:
        added_property.attrib["BaseType"] = base_type
    etree.SubElement(added_property, "Annotation", attrib={"Term": "OData.Description", "String": description})
    etree.SubElement(added_property, "Annotation", attrib={"Term": "OData.LongDescription", "String": longDescription})
    etree.SubElement(added_property, "Annotation", attrib={"Term": "OData.AdditionalProperties", "Bool": "false"})

    return added_property


def create_enum_property(property_name, enum_values, enum_description=None, enum_longDescription=None):
    """Creates a property of enum type to add to the CSDL schema."""
    enum_property_entry = etree.Element("EnumType", attrib={"Name": property_name})

    for value in enum_values:
        value_entry = etree.SubElement(enum_property_entry, "Member", attrib={"Name": value})
        description = enum_description.get(value) if enum_description else "TBD"
        longDescripton = enum_longDescription.get(value) if enum_longDescription else "TBD"
        etree.SubElement(value_entry, "Annotation", attrib={"Term": "OData.Description", "String": description})

    return enum_property_entry
    
type_conversion = {
    str: "Edm.String",
    float: "Edm.Decimal",
    bool: "Edm.Boolean",
    int: "Edm.Int64",
    "string": "Edm.String",
    "number": "Edm.Decimal",
    "boolean": "Edm.Boolean",
    "integer": "Edm.Int64",
}

def create_property_w_type(property_name, value=None, my_type=None, **kwargs):
    """Creates a base property using create_property based on the type value is"""
    entry = None
    my_type = type(value) if my_type is None else my_type
    if isinstance(value, list) or my_type in ["array", list] or kwargs.get('type') == "array":
        my_type = kwargs['items']['type'][0]
        entry = create_property(property_name, "Collection({})".format(type_conversion.get(my_type, 'TBD')), **kwargs)
    elif my_type in type_conversion:
        entry = create_property(property_name, type_conversion[my_type], **kwargs)
    else:
        entry = create_property(property_name, "TBD", **kwargs)

    return entry
    

class CsdlFile:
    """CSDL file that is created from the passed JSON"""
    def __init__(self, annotated_json, inherited_prop_list=[], csv=None):
        self.csdl = None
        self.main_csdl = None
        self.annotated_json = annotated_json
        # if the JSON input file is not a json-schema, build a database from the mockup
        if "$schema" in self.annotated_json:
           self._annotation_database = self.annotated_json["properties"]
           self._name = annotated_json['title']

           for key in list(self._annotation_database):
               if "@" in key:
                   del self._annotation_database[key]
        else:
           self._annotation_database = database_builder(self.annotated_json, csv)
           self._name = annotated_json['@odata.type']

        for item in inherited_prop_list:
            if item in self._annotation_database:
                del self._annotation_database[item]

    def __str__(self):
        return str(self.csdl)

    @property
    def name(self):
        """Returns the simple version of the @odata.type"""
        match = re.match(REGEX_TYPE, self._name)
        return match.group(1) if match else self._name

    @name.setter
    def name(self, name):
        """Sets the name property"""
        self._name = name

    def init_csdl(self):
        """Builds the header and the root of th CSDL file."""
        # self.csdl = etree.Element("Edmx", nsmap={"edmx":"http://docs.oasis-open.org/odata/ns/edmx"}, attrib={"Version": "4.0"})#etree.XML(CSDL_HEADER_TEMPLATE.format(self.name))
        self.main_csdl, self.csdl, _services = xml_convenience.create_xml_base(self.name.split('.')[0])
        self.entity = etree.Element('EntityType', {
            'Name': self.name.split('.')[0],
            'BaseType': '.'.join([self.name.split('.')[0]]*2)
        })
        self.csdl.append(self.entity)

    def build_csdl(self):
        for key, descriptors in self._annotation_database.items():
            self.build_csdl_node(self.entity, key, descriptors)
    
    def build_csdl_node(self, entry, key, descriptors):
        """Builds the csdl file from the annotated json database"""
        kwargs = {}
        if "description" in descriptors:
            kwargs["description"] = descriptors["description"]
        if "longDescription" in descriptors:
            kwargs["longDescription"] = descriptors["longDescription"]
        if key in RESOURCE_TYPES:
            entry.append(create_property(key, "Resource.{}".format(key)))
            return
        if "required" in descriptors:
            kwargs["required"] = True
        if "readonly" in descriptors:
            kwargs["readonly"] = False
        if "type" in descriptors:
            # JSON schema file
            kwargs["type"] = descriptors["type"]
        if "items" in descriptors:
            # JSON schema file
            kwargs["items"] = descriptors["items"]
        value = descriptors.get("value", None)
        if isinstance(value, dict) or "properties" in descriptors:
                # kwargs["base_name"] = "Resource.%s" % key
            if "$ref" in descriptors:
                # for jsonschema
                pass
            if "link" in descriptors:
                kwargs = {}
                kwargs['schema_name'] = descriptors['link']
                if not any([descriptors['link'] in x.attrib.get('Uri', '').split('/')[-1] for x in self.main_csdl]):
                    my_node = xml_convenience.add_reference(None, None, descriptors['link'])
                    self.main_csdl.insert(3, my_node)
                if descriptors.get("type") == "array":
                    kwargs['collection'] = True
                entry.append(create_navigation(key, **kwargs))
            else:
                complex_prop = create_complex_property(key, **kwargs)
                if descriptors.get("type") == "array":
                    entry.append(create_property(key, "Collection(%s.%s)" % (self.name, key), **kwargs))
                else:
                    entry.append(create_property(key, "%s.%s" % (self.name, key), **kwargs))
                for key, descriptors in descriptors["properties"].items():
                    self.build_csdl_node(complex_prop, key, descriptors)
                self.csdl.append(complex_prop)
        elif "enum" in descriptors:
            if descriptors.get("type") == "array":
                entry.append(create_property(key, "Collection(%s.%s)" % (self.name, key), **kwargs))
            else:
                entry.append(create_property(key, "%s.%s" % (self.name, key), **kwargs))
            self.csdl.append(create_enum_property(key, descriptors.get("enum"), descriptors.get("enumDescriptions", None), descriptors.get("enumLongDescriptions", None)))
        else:
            entry.append(create_property_w_type(key, value, **kwargs))

    def add_schema_link(self):
        #TODO: Add schema link to CSDL
        pass


def main():
    """ Main function """
    argget = argparse.ArgumentParser(description='Builds a mostly complete CSDL file from an annotated JSON file and an optional CSV file.')

    # Create Tool Arguments
    argget.add_argument('json', type=str, help='file to process')
    argget.add_argument('--desc', type=str, default='No desc', help='sysdescription for identifying logs')
    argget.add_argument('--csv', type=str, help='csv file of helpful definitions for this file')
    argget.add_argument('--toggle', action='store_true', help='print a csv report at the end of the log')

    args = argget.parse_args()

    # Get File
    file_name = args.json
    try:
        with open(file_name) as fle:
            file_data = fle.read()
            json_data = json.loads(file_data)
    except json.JSONDecodeError:
        sys.stderr.write("Unable to parse JSON file supplied.")
        return 1
    except Exception:
        sys.stderr.write("Problem getting file provided")
        return 1
    
    csv_dict = {}

    if args.csv:
        with open(args.csv) as f:
            csv_reader = csv.reader(f, delimiter='|')
            for line in csv_reader:
                csv_dict[line[0]] = line[1:]
        print(csv_dict)


    csdl = CsdlFile(json_data, RESOURCE_PROPERTIES, csv=csv_dict)
    csdl.init_csdl()
    csdl.build_csdl()
    output_xml = csdl.name+'.xml'

    with open(output_xml, 'w') as output:
        xml_string = etree.tostring(csdl.main_csdl, encoding="unicode", method="xml")
        xml_obj = xml.dom.minidom.parseString(xml_string)
        xml_string = xml_obj.toprettyxml()

        pretty_xml_as_string = xml_string
        pretty_xml_as_string_new = ''

        # input(pretty_xml_as_string)
        # post process Annotations
        priority_tags = ["xmlns", "xmlns:edmx", "Name", "Term", "Property", "Type", "Namespace", "EnumMember", "String", "Bool"]
        for line in pretty_xml_as_string.split('\n'):
            priority_tag_dict = {}
            other_tags = []
            allresults = re.findall('[a-zA-Z:]+?=".+?"', line)
            tokened_line = re.sub('[a-zA-Z:]+?=".+?"', 'xxToken', line)
            for tag in allresults:
                tag_name, tag_content = tuple(tag.split('=', 1))
                if tag_name not in priority_tags:
                    other_tags.append(tag_name)
                priority_tag_dict[tag_name] = tag

            for tag_name in priority_tags + other_tags:
                if tag_name in priority_tag_dict:
                    tokened_line = tokened_line.replace('xxToken', priority_tag_dict[tag_name], 1)

            tokened_line = tokened_line.replace('&quot;', '"')
            pretty_xml_as_string_new += tokened_line + '\n'
        output.write(CSDL_HEADER_TEMPLATE.format(csdl.name) + pretty_xml_as_string_new)
    #csdl.csdl.getroottree().write(output_xml, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    return 0

if __name__ == '__main__':
    sys.exit(main())