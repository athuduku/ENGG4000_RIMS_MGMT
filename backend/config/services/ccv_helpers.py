"""
CCV XML Parsing Helpers
-----------------------
Pure utility functions for extracting and converting data
from CCV (Common CV) XML files. No Django views or models here.
"""

import re
from datetime import datetime, date


# ─────────────────────────────────────────────
# Field Extraction
# ─────────────────────────────────────────────

def extract_field_value(section, label_name):
    for field in section.findall('field'):
        if field.get('label') != label_name:
            continue

        val = field.findtext('value')
        if val and val.strip():
            return val.strip()

        lov = field.findtext('lov')
        if lov and lov.strip():
            return lov.strip()

        lov_text = field.findtext('lov/text')
        if lov_text and lov_text.strip():
            return lov_text.strip()

        ref = field.find('refTable')
        if ref is not None:
            for link in ref.findall('linkedWith'):
                value = link.get('value')
                if value:
                    return value

    return None


def extract_organization(field):
    ref = field.find('refTable')
    if ref is None:
        return None

    for link in ref.findall('linkedWith'):
        if link.get('label') == 'Organization':
            return link.get('value')

    return None


def extract_department_for_org(xml_root, target_org=None):
    """
    Finds the department associated with the given organization.
    If target_org is None, returns the first department found.
    """
    fallback = None

    for section in xml_root.findall('.//section'):
        org  = None
        dept = None

        for field in section.findall('field'):
            label = field.get('label')
            if label == "Organization":
                org = extract_organization(field)
            elif label == "Department":
                dept = field.findtext('value')

        if dept:
            if not fallback:
                fallback = dept
            if target_org and org and target_org.lower() in org.lower():
                return dept

    return fallback


def extract_bilingual_value(field_elem):
    if field_elem is None:
        return None
    value_elem = field_elem.find('value')
    if value_elem is not None and value_elem.text:
        return value_elem.text
    bilingual = field_elem.find('bilingual/english')
    if bilingual is not None and bilingual.text:
        return bilingual.text
    return None


def extract_description(section):
    """Extract description from CCV bilingual fields."""
    for label in ['Description/Contribution Value/Impact', 'Contribution Value']:
        field = section.find(f'field[@label="{label}"]')
        if field is not None:
            bilingual = field.find('bilingual/english')
            if bilingual is not None and bilingual.text:
                return bilingual.text.strip()
            val = field.find('value')
            if val is not None:
                text = val.get('text')
                if text:
                    return text.strip()
            text = extract_field_value(section, label)
            if text:
                return text.strip()
    return None


# ─────────────────────────────────────────────
# Date Parsing
# ─────────────────────────────────────────────

def parse_date_from_yearmonth(date_str):
    """Convert yyyy/MM format to date object."""
    if not date_str:
        return None
    try:
        parts = date_str.split('/')
        year  = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        return datetime(year, month, 1).date()
    except Exception:
        return None


def parse_funding_date(date_str):
    """Parse funding date in various CCV formats → date object."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            year  = int(parts[0])
            month = int(parts[1].zfill(2)) if len(parts) > 1 else 1
            return datetime(year, month, 1).date()
        elif len(date_str) == 10 and date_str.count('-') == 2:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        elif len(date_str) == 4 and date_str.isdigit():
            return datetime(int(date_str), 1, 1).date()
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
    return None


# ─────────────────────────────────────────────
# Value Mapping
# ─────────────────────────────────────────────

def map_funding_role_to_choice(role_str):
    if not role_str:
        return 'other'
    r = role_str.lower()
    if 'principal investigator' in r: return 'pi'
    if 'co-investigator' in r:        return 'co_pi'
    if 'principal applicant' in r:    return 'pa'
    if 'co-applicant' in r:           return 'co_app'
    return 'other'


def determine_activity_category(title, topic, audience, event):
    text = f"{title or ''} {topic or ''} {audience or ''} {event or ''}".lower()

    # Conference checked FIRST — before workshop/seminar
    if any(w in text for w in ['conference', 'symposium', 'congress', 'summit']):
        return 'conference'
    if any(w in text for w in ['outreach', 'community', 'knowledge mobilization',
                                'public engagement', 'workshop', 'seminar',
                                'disabilities', 'partnership', 'gathering']):
        return 'knowledge_mobilization'
    if any(w in text for w in ['broadcast', 'interview', 'media', 'cbc',
                                'global news', 'radio', 'telegraph', 'news']):
        return 'media'
    if any(w in text for w in ['university', 'academic', 'research', 'lecture', 'presentation']):
        return 'academic'
    # meeting kept here — avoids "meeting" matching conference
    if 'meeting' in text:
        return 'conference'
    return 'conference' if event else 'other'


# ─────────────────────────────────────────────
# Record ID
# ─────────────────────────────────────────────

def get_record_id(section, fallback_parts):
    """
    Returns section's recordId if present.
    Falls back to a normalised string from fallback_parts if not.
    """
    record_id = section.get('recordId')
    if record_id:
        return record_id
    combined = '_'.join(str(p) for p in fallback_parts if p)
    return 'fallback:' + re.sub(r'[^a-z0-9_]', '', combined.lower())[:120]