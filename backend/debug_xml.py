#!/usr/bin/env python
"""
XML Parser Debug Script - Inspect CCV XML structure
Usage: python debug_xml.py /path/to/your/ccv/file.xml
"""

import xml.etree.ElementTree as ET
import sys

if len(sys.argv) < 2:
    print("Usage: python debug_xml.py <path_to_xml_file>")
    sys.exit(1)

xml_file = sys.argv[1]

try:
    tree = ET.parse(xml_file)
    root = tree.getroot()
    print(f"\nParsed XML file: {xml_file}\n")
except Exception as e:
    print(f"Error parsing XML: {e}")
    sys.exit(1)

print("="*80)
print("RESEARCH FUNDING HISTORY SECTIONS")
print("="*80 + "\n")

funding_sections = root.findall('.//section[@label="Research Funding History"]')
print(f"Found {len(funding_sections)} Research Funding History sections\n")

for idx, funding_section in enumerate(funding_sections, 1):
    print(f"\n--- FUNDING #{idx} ---")

    title_elem = None
    for field in funding_section.findall('field'):
        if field.get('label') == 'Funding Title':
            value_elem = field.find('value')
            lov_elem = field.find('lov')
            if value_elem is not None and value_elem.text:
                title_elem = value_elem.text.strip()
            elif lov_elem is not None and lov_elem.text:
                title_elem = lov_elem.text.strip()

    print(f"Title: {title_elem or 'NOT FOUND'}")

    print("\nTop-level fields in Research Funding History:")
    for field in funding_section.findall('field'):
        label = field.get('label')
        value = None
        value_elem = field.find('value')
        lov_elem = field.find('lov')

        if value_elem is not None and value_elem.text:
            value = value_elem.text.strip()
        elif lov_elem is not None and lov_elem.text:
            value = lov_elem.text.strip()

        print(f"  - {label}: {value or 'EMPTY'}")

    print("\n--- FUNDING SOURCES SUBSECTION ---")
    funding_sources = funding_section.findall('section[@label="Funding Sources"]')

    if funding_sources:
        for src_idx, source_section in enumerate(funding_sources, 1):
            print(f"\nFunding Sources #{src_idx}:")

            for field in source_section.findall('field'):
                label = field.get('label')
                value = None
                value_elem = field.find('value')
                lov_elem = field.find('lov')

                if value_elem is not None and value_elem.text:
                    value = value_elem.text.strip()
                elif lov_elem is not None and lov_elem.text:
                    value = lov_elem.text.strip()

                if label in ['Funding Organization', 'Funding Type', 'Total Funding', 'Portion of Funding Received']:
                    print(f"  {label}: {value or 'EMPTY'}")
                else:
                    print(f"  - {label}: {value or 'EMPTY'}")
    else:
        print("No Funding Sources subsection found!")

    print("\n--- FUNDING BY YEAR SUBSECTIONS ---")
    funding_by_year = funding_section.findall('section[@label="Funding by Year"]')

    if funding_by_year:
        for year_idx, year_section in enumerate(funding_by_year, 1):
            print(f"\nFunding by Year #{year_idx}:")

            for field in year_section.findall('field'):
                label = field.get('label')
                value = None
                value_elem = field.find('value')
                lov_elem = field.find('lov')

                if value_elem is not None and value_elem.text:
                    value = value_elem.text.strip()
                elif lov_elem is not None and lov_elem.text:
                    value = lov_elem.text.strip()

                if label in ['Start Date', 'End Date', 'Portion of Funding Received']:
                    print(f"  {label}: {value or 'EMPTY'}")
                else:
                    print(f"  - {label}: {value or 'EMPTY'}")
    else:
        print("No Funding by Year subsections found!")

    print("\n" + "="*80)

print("\nXML inspection complete!")