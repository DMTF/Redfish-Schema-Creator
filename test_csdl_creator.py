# Copyright Notice:
# Copyright 2017-2020 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Schema-Creator/blob/master/LICENSE.md

import pytest
import lxml.etree
from csdl_creator import CsdlFile, database_builder, create_navigation, create_property, create_enum_property

TEST_FULL_DATA = {
    "@odata.id": "/redfish/v1/Thingy/1",
    "@odata.type": "#Thingy.v1_0_0.Thingy",
    "Id": "1",
    "Name": "Big Thingy",
    "ThingType": "RackMount | Cheap | Expensive | Obsolete | Trendy",
	"ThingType!Required": True,
	"ThingType!Description": "The type of thingy that this thingy is - really...",
	"ThingType!LongDescription": "A long thingy description...",
    "IndicatorLED": "Off | Lit | Blinking",
	"IndicatorLED!ReadWrite": True,
    "Location": { },
    "ThingContainer" : {"ThingKnob" : "Twist", "ThingKnobCount": 5, "ThingButton": {"ButtonColor": "Red", "ButtonColor@Description": "Color of the button.", "ButtonActuation@Required": True,"ButtonActuation": .34}},
    "Status": {
        "State": "Enabled",
        "Health": "OK"
    },
    "PCIeSlots": {
        "@odata.id": "/redfish/v1/Chassis/1/PCIeSlots"
    },
	"PCIeSlots@Link": "PCIeDevice",
    "Thermal": {
        "@odata.id": "/redfish/v1/Chassis/1/Thermal"
    },
	"Thermal@Link": "Thermal",
    "Power": {
        "@odata.id": "/redfish/v1/Chassis/1/Power"
    }
}

@pytest.fixture
def csdlfile_class():
    test_class = CsdlFile(TEST_DATA)
    return test_class

@pytest.fixture
def built_csdlfile_class():
    test_class = CsdlFile(TEST_DATA)
    test_class.build_csdl()
    return test_class

class TestPropertyCreators:
    """Strongly tests the property entry creation functions"""
    def test_nav_tbd_schema(self):
        entry = create_navigation('ThingyHolder')
        assert(entry.tag == "NavigationProperty" and entry.get("Type") == "TBD.TBD" and entry.get("Nullable") == 'false' and entry.get("Name") == "ThingyHolder")

    def test_nav_named_schema(self):
        entry = create_navigation('ThingyHolder', schema_name="SchemaName")
        assert(entry.tag == "NavigationProperty" and entry.get("Type") == "SchemaName.SchemaName" and entry.get("Nullable") == 'false' and entry.get("Name") == "ThingyHolder")

    def test_nav_description(self):
        description = create_navigation('ThingyHolder', description="This is a description.")
        default_description = create_navigation('ThingyHolder')
        assert((description.tag == "NavigationProperty" and description.find("OData.Description").get("String") == "This is a description.") and\
               (default_description.tag == "NavigationProperty" and default_description.find("OData.Description").get("String") == "A link to ThingyHolder"))

    def test_nav_long_description(self):
        long_description = create_navigation('ThingyHolder', long_description="This is a long description.")
        default_long_description = create_navigation('ThingyHolder')
        assert((long_description.tag == "NavigationProperty" and long_description.find("OData.LongDescription").get("String") == "This is a long description.") and\
               (default_long_description.tag == "NavigationProperty" and default_long_description.find("OData.LongDescription").get("String") == "This property shall be a link to a resource collection of type ThingyHolder."))

    def test_property_defaults(self):
        entry = create_property("ThingProperty", "A.Type")
        annotations = entry.findall("Annotation")
        permissions = description = long_description = None

        for annotation in annotations:
            if annotation.get("Term") == "OData.Permissions":
                permissions = annotation
            elif annotation.get("Term") == "OData.Description":
                description = annotation
            elif annotation.get("Term") == "OData.LongDescription":
                long_description = annotation

        assert(entry.tag == "Property" and entry.get("Name") == "ThingProperty" and entry.get("Type") == "A.Type" and\
               permissions.get("EnumMember") == "OData.Permission/Read" and description.get("String") == "TBD" and long_description.get("String") == "TBD")

    def test_permissions(self):
        entry = create_property("ThingProperty", "A.Type", read_write=True)
        annotations = entry.findall("Annotation")
        permissions = None

        for annotation in annotations:
            if annotation.get("Term") == "OData.Permissions":
                permissions = annotation

        assert(entry.tag == "Property" and permissions.get("EnumMember") == "OData.Permission/ReadWrite")

    def test_description(self):
        entry = create_property("ThingProperty", "A.Type", description="A description.")
        annotations = entry.findall("Annotation")
        description = None

        for annotation in annotations:
            if annotation.get("Term") == "OData.Description":
                description = annotation

        assert(entry.tag == "Property" and description.get("String") == "A description.")

    def test_long_description(self):
        entry = create_property("ThingProperty", "A.Type", long_description="A long description.")
        annotations = entry.findall("Annotation")
        long_description = None

        for annotation in annotations:
            if annotation.get("Term") == "OData.LongDescription":
                long_description = annotation

        assert(entry.tag == "Property" and long_description.get("String") == "A long description.")

    def test_enum_property(self):
        entry = create_enum_property("AnEnum", ["A", "B", "C", "D"])
        annotations = entry.findall("Member")

        assert(all([True if item.get("Name") in ["A", "B", "C", "D"] else False \
                    for item in annotations]))

class TestDatabaseBuilder:
    """Strongly tests the database building function"""
    def test_builder(self):
        final_dict = {}
        database_builder(TEST_FULL_DATA, final_dict)
        assert("ThingKnob" in final_dict["ThingContainer"] and\
               "ButtonColor" in final_dict["ThingContainer"]["ThingButton"] and\
               final_dict["ThingContainer"]["ThingButton"]["ButtonColor"]["description"]=="Color of the button." and\
               final_dict["ThingContainer"]["ThingButton"]["ButtonActuation"]["required"]==True)

    def test_description_annotation(self):
        final_dict = {}
        database_builder(TEST_FULL_DATA, final_dict)

        assert(final_dict['ThingType']['description'] == "The type of thingy that this thingy is - really...")

    def test_longdescription_annotation(self):
        final_dict = {}
        database_builder(TEST_FULL_DATA, final_dict)

        assert(final_dict['ThingType']['longdescription'] == "A long thingy description...")

    def test_link_annotation(self):
        final_dict = {}
        database_builder(TEST_FULL_DATA, final_dict)

        assert(final_dict['PCIeSlots']['link'] == "PCIeDevice")

    def test_readwrite_annotation(self):
        final_dict = {}
        database_builder(TEST_FULL_DATA, final_dict)

        assert(final_dict['IndicatorLED']['readwrite'] == True)

    def test_required_annotation(self):
        final_dict = {}
        database_builder(TEST_FULL_DATA, final_dict)

        assert(final_dict['ThingType']['required'] == True)

    def test_enum_annotation(self):
        final_dict = {}
        database_builder(TEST_FULL_DATA, final_dict)

        assert(all([True if item in ["RackMount", "Cheap", "Expensive", "Obsolete", "Trendy"] else False \
                    for item in final_dict['ThingType']['value']]))

    def test_enum_w_empty_annotation(self):
        final_dict = {}
        database_builder({"ThingType": "|RackMount | Cheap | Expensive | Obsolete | Trendy|"}, final_dict)

        assert(all([True if item in ["RackMount", "Cheap", "Expensive", "Obsolete", "Trendy"] else False \
                    for item in final_dict['ThingType']['value']]))

class TestCsdlFile:
    def test_name(self):
        test_class = CsdlFile(TEST_FULL_DATA)
        assert(test_class.name == 'Thingy.v1_0_0')

    def test_build_csdl(self):
        test_class = CsdlFile(TEST_FULL_DATA)
        test_class.build_csdl()

        assert(test_class._annotation_database is not {})
