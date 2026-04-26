"""
CCV XML Parser
--------------
All parse_xml_* functions for importing CCV data into RIMS.
Depends on ccv_helpers for pure utility functions.
"""

import re
import logging
import uuid
import secrets

from datetime import datetime, date
from django.db import transaction

from .ccv_helpers import (
    extract_field_value,
    extract_bilingual_value,
    extract_description,
    parse_date_from_yearmonth,
    parse_funding_date,
    map_funding_role_to_choice,
    determine_activity_category,
    get_record_id,
)

from config.models import (
    CustomUser, ResearcherProfile, StudentNotification, StudentProfile
)
from config.utils import log_action

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CCV Structure Validation
# ─────────────────────────────────────────────

def validate_ccv_structure(root, user_type='researcher'):
    common_sections     = ['Personal Information']
    researcher_sections = ['Activities', 'Publications']

    required = common_sections
    if user_type == 'researcher':
        required += researcher_sections

    for section in required:
        if root.find(f'.//section[@label="{section}"]') is None:
            return False, f'Missing required section: {section}'
    return True, None


# ─────────────────────────────────────────────
# Student Proxy Helper
# ─────────────────────────────────────────────

def get_student_researcher_proxy(user):
    """
    Returns the ResearcherProfile used to store a student's
    publications and activities. Creates one if absent.

    NOTE: This is NOT a real researcher profile.
    The associated user has user_type='student'.
    Do NOT use this for researcher-only queries.

    Raises:
        ValueError: if called with a non-student user.
    """
    if user.user_type != 'student':
        raise ValueError(
            f"get_student_researcher_proxy() called with non-student user: "
            f"{user.email} (type={user.user_type})"
        )

    profile, created = ResearcherProfile.objects.get_or_create(
        user=user,
        defaults={'research_interests': ''}
    )

    if created:
        try:
            log_action(
                None, 'other', target=profile,
                summary=f'ResearcherProfile proxy created for student {user.email}'
            )
        except Exception:
            pass

    return profile


# ─────────────────────────────────────────────
# Supervision Linking Helpers
# ─────────────────────────────────────────────

def try_link_student(record):
    from config.models import StudentProfile, StudentNotification

    if record.linked_student:
        return

    clean = re.sub(r'[^a-zA-Z\s]', '', record.student_name.lower()).strip()
    parts = clean.split()
    if len(parts) < 2:
        return

    first, last = parts[0], parts[-1]

    def _notify_and_link(student):
        record.linked_student = student
        record.save(update_fields=['linked_student'])
        already = StudentNotification.objects.filter(
            user=student.user,
            message__icontains="supervision record for you"
        ).exists()
        if not already:
            StudentNotification.objects.create(
                user=student.user,
                message=(
                    f'{record.researcher.user.get_full_name()} appears as your supervisor in a record. '
                    f'If they are your current supervisor, you can send them a request from your profile.'
                )
            )

    matches = StudentProfile.objects.filter(
        user__first_name__iexact=first,
        user__last_name__iexact=last,
    )
    if matches.count() == 1:
        _notify_and_link(matches.first())
        return

    if matches.count() == 0:
        reversed_matches = StudentProfile.objects.filter(
            user__first_name__iexact=last,
            user__last_name__iexact=first,
        )
        if reversed_matches.count() == 1:
            _notify_and_link(reversed_matches.first())


def reverse_link_supervision(user):
    """When a student registers, check if any supervision records match them."""
    from config.models import SupervisionRecord
    from django.db.models import Q

    try:
        profile = user.student_profile
    except Exception:
        return

    clean = re.sub(r'[^a-zA-Z\s]', '', user.get_full_name().lower()).strip()
    parts = clean.split()
    if len(parts) < 2:
        return

    first, last = parts[0], parts[-1]

    unlinked = SupervisionRecord.objects.filter(
        linked_student__isnull=True,
    ).filter(
        Q(student_name__iexact=f"{first} {last}") |
        Q(student_name__iexact=f"{last} {first}")
    )

    for record in unlinked:
        try_link_student(record)


# ─────────────────────────────────────────────
# Publication Author Linking
# ─────────────────────────────────────────────

def auto_link_publication_authors(publication):
    from config.models import PublicationAuthor, StudentProfile, ResearcherProfile, StudentNotification

    if not publication.authors:
        return

    raw = publication.authors.replace('*', '').strip()
    if ';' in raw:
        authors_list = [a.strip().lower() for a in raw.split(';') if a.strip()]
    else:
        authors_list = [a.strip().lower() for a in raw.split(',') if a.strip()]

    candidate_last_names = set()
    for author in authors_list:
        if ',' in author:
            candidate_last_names.add(author.split(',')[0].strip())
        else:
            parts = author.split()
            if parts:
                candidate_last_names.add(parts[-1].strip())

    if not candidate_last_names:
        return

    def is_match(user):
        full_name  = user.get_full_name().lower().strip()
        last_name  = user.last_name.lower().strip()
        first_name = user.first_name.lower().strip()

        if not full_name or not last_name or len(last_name) < 3:
            return False

        for author in authors_list:
            author = author.strip()
            if full_name == author:
                return True
            if ',' in author:
                parts   = [p.strip() for p in author.split(',', 1)]
                a_last  = parts[0]
                a_first = parts[1] if len(parts) > 1 else ''
                if a_last == last_name:
                    if not a_first:
                        return True
                    if first_name and (first_name == a_first or first_name[0] == a_first[0]):
                        return True
                continue
            author_parts = author.split()
            if len(author_parts) >= 2:
                if last_name == author_parts[-1]:
                    if first_name and (first_name == author_parts[0] or first_name[0] == author_parts[0][0]):
                        return True
            if len(author.split()) == 1 and author == last_name:
                return True
        return False

    for student in StudentProfile.objects.select_related('user').filter(
        user__last_name__in=candidate_last_names
    ):
        if student.user.id == publication.researcher.user.id:
            continue
        if is_match(student.user):
            PublicationAuthor.objects.get_or_create(
                publication=publication, student=student,
            )

    for researcher in ResearcherProfile.objects.select_related('user').filter(
        user__last_name__in=candidate_last_names
    ):
        if researcher.id == publication.researcher.id:
            continue
        if is_match(researcher.user):
            StudentNotification.objects.get_or_create(
                user=researcher.user,
                message=f'You are listed as a co-author on "{publication.title}" by {publication.researcher.user.get_full_name()}.',
            )


# ─────────────────────────────────────────────
# parse_xml_education
# ─────────────────────────────────────────────

def parse_xml_education(researcher, xml_root):
    from config.models import Education

    seen_ids = set()
    count_created = count_updated = 0

    for edu_section in xml_root.findall('.//section[@label="Education"]'):
        for degree_section in edu_section.findall('section[@label="Degrees"]'):
            degree_type    = extract_field_value(degree_section, 'Degree Type')
            specialization = extract_field_value(degree_section, 'Specialization')
            degree_name    = extract_field_value(degree_section, 'Degree Name')

            organization = None
            org_field    = degree_section.find('field[@label="Organization"]')
            if org_field is not None:
                reftable = org_field.find('refTable')
                if reftable is not None:
                    linked = reftable.find('linkedWith[@label="Organization"]')
                    if linked is not None:
                        organization = linked.get('value')
            if not organization:
                organization = extract_field_value(degree_section, 'Other Organization')

            completion_date = extract_field_value(degree_section, 'Degree Received Date')
            if not degree_type:
                continue

            start_date_str = extract_field_value(degree_section, 'Degree Start Date')
            start_date = parse_date_from_yearmonth(start_date_str) if start_date_str else None

            expected_date = None
            if completion_date:
                try:
                    expected_date = (
                        parse_date_from_yearmonth(completion_date)
                        if '/' in completion_date
                        else (datetime.strptime(f"{completion_date}-01-01", "%Y-%m-%d").date()
                              if len(completion_date) == 4 else None)
                    )
                except Exception:
                    pass

            if not expected_date:
                expected_date_str = extract_field_value(degree_section, 'Degree Expected Date')
                if expected_date_str:
                    expected_date = parse_date_from_yearmonth(expected_date_str)

            thesis_title = extract_field_value(degree_section, 'Thesis Title') or ''
            ext_id = get_record_id(degree_section, [degree_type, organization, completion_date])
            seen_ids.add(ext_id)

            fields = dict(
                degree_type    = degree_type[:100],
                specialization = specialization or degree_name or '',
                institution    = organization or 'Unknown',
                thesis_title   = thesis_title,
                start_date     = start_date,
                expected_date  = expected_date,
            )

            existing = Education.objects.filter(
                researcher=researcher, external_id=ext_id
            ).first()

            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                existing.save()
                count_updated += 1
            else:
                Education.objects.create(
                    researcher=researcher, external_id=ext_id, **fields
                )
                count_created += 1

    Education.objects.filter(
        researcher=researcher
    ).exclude(external_id__in=seen_ids).delete()

    return count_created + count_updated


# ─────────────────────────────────────────────
# parse_xml_funding
# ─────────────────────────────────────────────

def parse_xml_funding(researcher, xml_root):
    from config.models import Funding, Project
    from django.utils import timezone

    seen_ids = set()
    count_created = count_updated = 0

    for funding_section in xml_root.findall('.//section[@label="Research Funding History"]'):
        status_val = extract_field_value(funding_section, 'Funding Status') or ''
        if status_val == 'Under Review':
            continue

        s = status_val.lower()
        if 'award' in s or 'funded' in s or 'completed' in s:
            inferred_status = 'awarded'
        elif 'rejected' in s or 'unsuccessful' in s or 'declined' in s:
            inferred_status = 'rejected'
        elif 'submitted' in s or 'review' in s or 'pending' in s:
            inferred_status = 'submitted'
        else:
            inferred_status = 'awarded'

        title = extract_field_value(funding_section, 'Funding Title')
        if not title:
            continue

        parent_rid = funding_section.get('recordId', '')
        linked_project = Project.all_objects.filter(
            researcher=researcher, external_id=parent_rid,
        ).first()

        funding_type = extract_field_value(funding_section, 'Funding Type')
        funding_role = map_funding_role_to_choice(
            extract_field_value(funding_section, 'Funding Role')
        )

        org = program_name = None
        currency = 'CAD'

        for source_section in funding_section.findall('section[@label="Funding Sources"]'):
            org = (extract_field_value(source_section, 'Funding Organization') or
                   extract_field_value(source_section, 'Other Funding Organization'))
            program_name = extract_field_value(source_section, 'Program Name')
            currency_str = extract_field_value(source_section, 'Currency of Total Funding') or ''
            currency = 'USD' if 'united states' in currency_str.lower() else 'CAD'
            break

        if not org:
            continue

        year_sections = funding_section.findall('section[@label="Funding by Year"]')

        if year_sections:
            for ys in year_sections:
                total = extract_field_value(ys, 'Total Funding')
                try:
                    amount = float(total) if total else 0
                except Exception:
                    amount = 0
                if amount <= 0:
                    continue

                year_portion = extract_field_value(ys, 'Portion of Funding Received')
                try:
                    year_portion_val = float(year_portion) if year_portion else None
                    if year_portion_val == 0:
                        year_portion_val = None
                except Exception:
                    year_portion_val = None

                co_i_roles = ('co_pi', 'co_app', 'other', 'collaborator')
                if funding_role in co_i_roles:
                    amount = year_portion_val or 0

                ibme_val = year_portion_val
                start = parse_funding_date(extract_field_value(ys, 'Start Date'))
                end   = parse_funding_date(extract_field_value(ys, 'End Date'))

                ext_id = get_record_id(ys, [funding_section.get('recordId', ''), str(start)])
                seen_ids.add(ext_id)

                fields = dict(
                    title=title, organization=org, funding_type=funding_type,
                    program_name=program_name, amount=amount, amount_to_ibme=ibme_val,
                    start_date=start, end_date=end,
                    role=funding_role, status=inferred_status,
                    project=linked_project, currency=currency,
                )

                existing = Funding.all_objects.filter(
                    researcher=researcher, external_id=ext_id
                ).first()

                if existing:
                    if existing.is_deleted:
                        existing.is_deleted = False
                        existing.deleted_at = None
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    existing.save()
                    count_updated += 1
                else:
                    Funding.objects.create(
                        researcher=researcher, external_id=ext_id, **fields
                    )
                    count_created += 1

        else:
            for source_section in funding_section.findall('section[@label="Funding Sources"]'):
                src_org = (extract_field_value(source_section, 'Funding Organization') or
                           extract_field_value(source_section, 'Other Funding Organization'))
                if not src_org:
                    continue

                src_program  = extract_field_value(source_section, 'Program Name') or program_name
                portion_str  = extract_field_value(source_section, 'Portion of Funding Received')
                total_str    = extract_field_value(source_section, 'Total Funding')
                currency_str = extract_field_value(source_section, 'Currency of Total Funding') or ''
                src_currency = 'USD' if 'united states' in currency_str.lower() else 'CAD'

                try:
                    grant_total = float(total_str) if total_str else 0
                except Exception:
                    grant_total = 0

                try:
                    portion_val = float(portion_str) if (
                        portion_str is not None and str(portion_str).strip() != ''
                    ) else None
                except Exception:
                    portion_val = None

                amount = portion_val if portion_val is not None else grant_total

                if amount <= 0 and portion_val is None and grant_total <= 0:
                    continue

                ibme_amount = portion_val if (portion_val and portion_val > 0) else None

                src_start = parse_funding_date(
                    extract_field_value(source_section, 'Funding Start Date') or
                    extract_field_value(funding_section, 'Funding Start Date')
                )
                src_end = parse_funding_date(
                    extract_field_value(source_section, 'Funding End Date') or
                    extract_field_value(funding_section, 'Funding End Date')
                )

                src_record_id = source_section.get('recordId', '')
                ext_id = get_record_id(
                    source_section, [title, src_org, str(src_start), src_record_id]
                )
                seen_ids.add(ext_id)

                fields = dict(
                    title=title, organization=src_org, funding_type=funding_type,
                    program_name=src_program, amount=amount,
                    amount_to_ibme=ibme_amount, grant_total=grant_total,
                    start_date=src_start, end_date=src_end,
                    role=funding_role, status=inferred_status,
                    project=linked_project, currency=src_currency,
                )

                existing = Funding.all_objects.filter(
                    researcher=researcher, external_id=ext_id
                ).first()

                if existing:
                    if existing.is_deleted:
                        existing.is_deleted = False
                        existing.deleted_at = None
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    existing.save()
                    count_updated += 1
                else:
                    Funding.objects.create(
                        researcher=researcher, external_id=ext_id, **fields
                    )
                    count_created += 1

    Funding.objects.filter(
        researcher=researcher
    ).exclude(external_id__in=seen_ids).update(
        is_deleted=True, deleted_at=timezone.now()
    )

    return count_created + count_updated


# ─────────────────────────────────────────────
# parse_xml_recognitions
# ─────────────────────────────────────────────

def parse_xml_recognitions(researcher, xml_root):
    from config.models import Recognition

    seen_ids = set()
    count_created = count_updated = 0

    for recog_section in xml_root.findall('.//section[@label="Recognitions"]'):
        award_name = extract_field_value(recog_section, 'Recognition Name')
        if not award_name:
            continue

        amount_str = extract_field_value(recog_section, 'Amount')
        amount = None
        if amount_str:
            try:
                amount = float(amount_str)
            except Exception:
                pass

        start_date       = parse_funding_date(extract_field_value(recog_section, 'Effective Date'))
        end_date         = parse_funding_date(extract_field_value(recog_section, 'End Date'))
        recognition_type = extract_field_value(recog_section, 'Recognition Type')

        organization = None
        org_field = recog_section.find('field[@label="Organization"]')
        if org_field is not None:
            reftable = org_field.find('refTable')
            if reftable is not None:
                linked = reftable.find('linkedWith[@label="Organization"]')
                if linked is not None:
                    organization = linked.get('value')
        if not organization:
            organization = extract_field_value(recog_section, 'Other Organization') or ''

        ext_id = get_record_id(recog_section, [award_name, str(start_date)])
        seen_ids.add(ext_id)

        fields = dict(
            name             = award_name,
            organization     = organization,
            amount           = amount,
            recognition_type = recognition_type,
            start_date       = start_date,
            end_date         = end_date,
            description      = extract_field_value(recog_section, 'Description') or '',
        )

        existing = Recognition.objects.filter(
            researcher=researcher, external_id=ext_id
        ).first()

        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            existing.save()
            count_updated += 1
        else:
            Recognition.objects.create(
                researcher=researcher, external_id=ext_id, **fields
            )
            count_created += 1

    Recognition.objects.filter(
        researcher=researcher
    ).exclude(external_id__in=seen_ids).delete()

    return count_created + count_updated


# ─────────────────────────────────────────────
# parse_xml_publications
# ─────────────────────────────────────────────

def parse_xml_publications(researcher, xml_root):
    from config.models import Publication

    seen_external_ids = set()
    count_created = count_updated = 0

    publication_labels = [
        ("Journal Articles",       "Article Title",     "journal"),
        ("Conference Publications", "Publication Title", "conference"),
        ("Book Chapters",           "Chapter Title",     "chapter"),
        ("Patents",                 "Patent Title",      "patent"),
    ]

    for label, title_field, pub_type in publication_labels:
        for pub_section in xml_root.findall(f'.//section[@label="{label}"]'):
            title = extract_field_value(pub_section, title_field)
            if not title:
                continue

            ext_id = get_record_id(pub_section, [title, pub_type])
            seen_external_ids.add(ext_id)

            authors = extract_field_value(pub_section, 'Authors')
            doi = status = None
            status = 'published'
            description = None
            (journal, year_str, volume, issue, pages, publisher,
             open_access, refereed, invited, conference_location,
             book_title, editors, publication_location, contribution_role,
             patent_number, country, filing_date) = [None] * 17

            if label == "Journal Articles":
                journal           = extract_field_value(pub_section, 'Journal')
                year_str          = extract_field_value(pub_section, 'Year')
                volume            = extract_field_value(pub_section, 'Volume')
                issue             = extract_field_value(pub_section, 'Issue')
                pages             = extract_field_value(pub_section, 'Page Range')
                publisher         = extract_field_value(pub_section, 'Publisher')
                description       = (extract_field_value(pub_section, 'Abstract') or
                                     extract_field_value(pub_section, 'Description/Contribution Value/Impact'))
                doi               = extract_field_value(pub_section, 'DOI')
                if isinstance(doi, dict):
                    doi = doi.get('value', {}).get('text')
                if not doi:
                    url_val = extract_field_value(pub_section, 'URL')
                    if isinstance(url_val, list):
                        url_val = url_val[0] if url_val else None
                    if url_val:
                        url_val = str(url_val).strip()
                        if url_val.upper().startswith('DOI:'):
                            doi = url_val[4:].strip()
                        elif 'doi.org/' in url_val.lower():
                            doi = url_val.split('doi.org/')[1].strip()
                if doi:
                    doi = str(doi).replace('https://', '').replace('http://', '').strip()
                contribution_role = extract_field_value(pub_section, 'Contribution Role')
                editors           = extract_field_value(pub_section, 'Editors')
                oa_str            = extract_field_value(pub_section, 'Open Access?')
                open_access       = True if oa_str and oa_str.lower() == 'yes' else (False if oa_str else None)
                ref_str           = extract_field_value(pub_section, 'Refereed?')
                refereed          = True if ref_str and ref_str.lower() == 'yes' else (False if ref_str else None)
                s = (extract_field_value(pub_section, 'Publishing Status') or '').lower()
                if 'revision' in s:                   status = 'revision_requested'
                elif 'rejected' in s:                 status = 'rejected'
                elif 'accepted' in s or 'press' in s: status = 'accepted'
                elif 'under review' in s:             status = 'under_review'

            elif label == "Conference Publications":
                journal             = extract_field_value(pub_section, 'Conference Name')
                year_str            = extract_field_value(pub_section, 'Conference Date')
                pages               = extract_field_value(pub_section, 'Page Range')
                conference_location = extract_field_value(pub_section, 'Conference Location')
                city                = extract_field_value(pub_section, 'City')
                if conference_location and city:
                    conference_location = f"{city}, {conference_location}"
                elif city:
                    conference_location = city
                doi         = extract_field_value(pub_section, 'DOI')
                description = (extract_field_value(pub_section, 'Abstract') or
                               extract_field_value(pub_section, 'Description/Contribution Value/Impact'))
                if isinstance(doi, dict):
                    doi = doi.get('value', {}).get('text')
                if not doi:
                    url_val = extract_field_value(pub_section, 'URL')
                    if isinstance(url_val, list):
                        url_val = url_val[0] if url_val else None
                    if url_val:
                        url_val = str(url_val).strip()
                        if url_val.upper().startswith('DOI:'):
                            doi = url_val[4:].strip()
                        elif 'doi.org/' in url_val.lower():
                            doi = url_val.split('doi.org/')[1].strip()
                if doi:
                    doi = str(doi).replace('https://', '').replace('http://', '').strip()
                contribution_role    = extract_field_value(pub_section, 'Contribution Role')
                editors              = extract_field_value(pub_section, 'Editors')
                publisher            = extract_field_value(pub_section, 'Publisher')
                publication_location = extract_field_value(pub_section, 'Publication Location')
                inv_str              = extract_field_value(pub_section, 'Invited?')
                invited              = True if inv_str and inv_str.lower() == 'yes' else (False if inv_str else None)
                ref_str              = extract_field_value(pub_section, 'Refereed?')
                refereed             = True if ref_str and ref_str.lower() == 'yes' else (False if ref_str else None)

            elif label == "Book Chapters":
                book_title        = extract_field_value(pub_section, 'Book Title')
                journal           = book_title
                year_str          = extract_field_value(pub_section, 'Year')
                pages             = extract_field_value(pub_section, 'Page Range')
                publisher         = extract_field_value(pub_section, 'Publisher')
                editors           = extract_field_value(pub_section, 'Editors')
                contribution_role = extract_field_value(pub_section, 'Contribution Role')
                doi               = extract_field_value(pub_section, 'DOI')
                description       = (extract_field_value(pub_section, 'Abstract') or
                                     extract_field_value(pub_section, 'Description/Contribution Value/Impact'))
                if isinstance(doi, dict):
                    doi = doi.get('value', {}).get('text')
                if not doi:
                    url_val = extract_field_value(pub_section, 'URL')
                    if isinstance(url_val, list):
                        url_val = url_val[0] if url_val else None
                    if url_val:
                        url_val = str(url_val).strip()
                        if url_val.upper().startswith('DOI:'):
                            doi = url_val[4:].strip()
                        elif 'doi.org/' in url_val.lower():
                            doi = url_val.split('doi.org/')[1].strip()
                if doi:
                    doi = str(doi).replace('https://', '').replace('http://', '').strip()
                publication_location = extract_field_value(pub_section, 'Publication Location')
                volume               = extract_field_value(pub_section, 'Volume')
                ref_str              = extract_field_value(pub_section, 'Refereed?')
                refereed             = True if ref_str and ref_str.lower() == 'yes' else (False if ref_str else None)

            elif label == "Patents":
                patent_number   = extract_field_value(pub_section, 'Patent Number')
                journal         = patent_number
                country         = extract_field_value(pub_section, 'Patent Location')
                authors         = (extract_field_value(pub_section, 'Inventors') or
                                   extract_field_value(pub_section, 'Authors') or
                                   researcher.user.get_full_name())
                filing_date_str = extract_field_value(pub_section, 'Filing Date')
                year_str        = extract_field_value(pub_section, 'Year Issued') or filing_date_str
                if filing_date_str and len(filing_date_str.strip()) == 10:
                    try:
                        filing_date = datetime.strptime(filing_date_str.strip(), '%Y-%m-%d').date()
                    except Exception:
                        filing_date = None
                patent_status = extract_field_value(pub_section, 'Patent Status') or ''
                status = ('granted'
                          if 'grant' in patent_status.lower() or 'issued' in patent_status.lower()
                          else 'pending')
                description = extract_description(pub_section)

            pub_date = None
            if year_str:
                try:
                    if '/' in year_str and len(year_str) in (6, 7):
                        pub_date = parse_date_from_yearmonth(year_str)
                    elif len(year_str.strip()) == 10 and '-' in year_str:
                        pub_date = datetime.strptime(year_str.strip(), "%Y-%m-%d").date()
                    elif len(year_str.strip()) == 4:
                        pub_date = date(int(year_str.strip()), 1, 1)
                except Exception:
                    pass

            if not pub_date:
                fallback = (extract_field_value(pub_section, 'Year') or
                            extract_field_value(pub_section, 'Year Issued'))
                if fallback and len(fallback.strip()) == 4:
                    try:
                        pub_date = date(int(fallback.strip()), 1, 1)
                    except Exception:
                        pass

            if not pub_date:
                continue

            language   = extract_field_value(pub_section, 'Language')
            pub_fields = dict(
                title=title[:500], authors=authors or 'Unknown', journal=journal or '',
                publication_date=pub_date, doi=doi, publication_type=pub_type, status=status,
                language=language, pages=pages, refereed=refereed,
                contribution_role=contribution_role,
                publication_location=publication_location, volume=volume, issue=issue,
                publisher=publisher, open_access=open_access,
                conference_location=conference_location, invited=invited,
                book_title=book_title, editors=editors, patent_number=patent_number,
                country=country, filing_date=filing_date, is_active=True,
                abstract=description,
            )

            existing = Publication.all_objects.filter(
                researcher=researcher, external_id=ext_id
            ).first()

            if not existing:
                existing = Publication.all_objects.filter(
                    researcher=researcher,
                    title__iexact=title,
                    publication_date=pub_date,
                    source='manual',
                ).first()
                if existing:
                    existing.source      = 'ccv'
                    existing.external_id = ext_id
                    logger.info(f"[CCV] Manual publication '{title}' claimed by CCV import")

            if existing:
                if existing.is_deleted:
                    seen_external_ids.add(ext_id)
                    continue
                MANUAL_STATUSES = ['accepted', 'under_review', 'revision_requested', 'draft']
                if existing.status in MANUAL_STATUSES:
                    pub_fields['status'] = existing.status
                for field, value in pub_fields.items():
                    setattr(existing, field, value)
                existing.is_active = True
                existing.save()
                auto_link_publication_authors(existing)
                count_updated += 1
            else:
                new_pub = Publication.objects.create(
                    researcher=researcher, external_id=ext_id, **pub_fields,
                )
                auto_link_publication_authors(new_pub)
                count_created += 1

    Publication.objects.filter(
        researcher=researcher, is_active=True
    ).exclude(external_id__in=seen_external_ids).update(is_active=False)

    return count_created + count_updated


# ─────────────────────────────────────────────
# parse_xml_activities
# ─────────────────────────────────────────────

def parse_xml_activities(researcher, xml_root):
    from config.models import Activity

    seen_external_ids = set()
    count_created = count_updated = 0

    for label in ["Presentations", "Broadcast Interviews", "Text Interviews"]:
        for activity_section in xml_root.findall(f'.//section[@label="{label}"]'):
            title = event = date_str = topic = co_presenters = audience = None
            invited = keynote = network = forum = city = country = None
            description = None

            if label == "Presentations":
                title         = extract_field_value(activity_section, 'Presentation Title')
                event         = extract_field_value(activity_section, 'Conference / Event Name')
                country       = extract_field_value(activity_section, 'Location')
                city          = extract_field_value(activity_section, 'City')
                date_str      = extract_field_value(activity_section, 'Presentation Year')
                activity_type = 'presentation'
                co_presenters = extract_field_value(activity_section, 'Co-Presenters')
                audience      = extract_field_value(activity_section, 'Main Audience')
                invited       = extract_field_value(activity_section, 'Invited?')
                keynote       = extract_field_value(activity_section, 'Keynote?')
                description   = extract_field_value(activity_section, 'Description / Contribution Value')
            elif label == "Broadcast Interviews":
                topic         = extract_field_value(activity_section, 'Topic')
                title         = topic or extract_field_value(activity_section, 'Program')
                network       = extract_field_value(activity_section, 'Network')
                event         = network
                date_str      = extract_field_value(activity_section, 'First Broadcast Date')
                activity_type = 'broadcast'
                description   = extract_field_value(activity_section, 'Description / Contribution Value')
            elif label == "Text Interviews":
                topic         = extract_field_value(activity_section, 'Topic')
                title         = topic
                forum         = extract_field_value(activity_section, 'Forum')
                event         = forum
                date_str      = extract_field_value(activity_section, 'Publication Date')
                activity_type = 'text_interview'
                description   = extract_field_value(activity_section, 'Description / Contribution Value')

            if not title:
                continue

            activity_date = None
            if date_str:
                try:
                    ds = date_str.strip()
                    if len(ds) == 10 and ds.count('-') == 2:
                        activity_date = datetime.strptime(ds, "%Y-%m-%d").date()
                    elif len(ds) == 4:
                        activity_date = date(int(ds), 1, 1)
                    else:
                        activity_date = parse_date_from_yearmonth(date_str)
                except Exception:
                    pass

            if not activity_date:
                continue

            if city and country:
                location = f"{city}, {country}"
            elif city:
                location = city
            elif country:
                location = country
            else:
                location = None

            def to_bool(val):
                if val is None:
                    return None
                return val.strip().lower() in ('yes', 'true', '1')

            category = determine_activity_category(title, topic, audience, event)
            ext_id   = get_record_id(activity_section, [title, str(activity_date), activity_type])
            seen_external_ids.add(ext_id)

            act_fields = dict(
                activity_type = activity_type,
                title         = title[:255],
                description   = description or event or '',
                date          = activity_date,
                category      = category,
                is_active     = True,
                source        = 'ccv',
                location      = location,
                invited       = to_bool(invited),
                keynote       = to_bool(keynote),
                co_presenters = co_presenters or '',
                audience      = audience or '',
            )

            existing = Activity.all_objects.filter(
                researcher=researcher, external_id=ext_id, source='ccv',
            ).first()

            if not existing:
                existing = Activity.all_objects.filter(
                    researcher=researcher, title__iexact=title,
                    date=activity_date, source='manual',
                ).first()
                if existing:
                    existing.source      = 'ccv'
                    existing.external_id = ext_id
                    logger.info(f"[CCV] Manual activity '{title}' claimed by CCV import")

            if existing:
                if existing.is_deleted:
                    seen_external_ids.add(ext_id)
                    continue
                manual_category = existing.category
                for k, v in act_fields.items():
                    setattr(existing, k, v)
                if existing.source == 'ccv' and manual_category:
                    existing.category = manual_category
                existing.is_active = True
                existing.save()
                count_updated += 1
            else:
                Activity.objects.create(
                    researcher=researcher, external_id=ext_id, **act_fields,
                )
                count_created += 1

    Activity.objects.filter(
        researcher=researcher, source='ccv', is_active=True
    ).exclude(external_id__in=seen_external_ids).update(is_active=False)

    return count_created + count_updated


# ─────────────────────────────────────────────
# parse_xml_projects
# ─────────────────────────────────────────────

def parse_xml_projects(researcher, xml_root):
    from config.models import Project, ProjectMember

    seen_external_ids = set()
    count_created = count_updated = 0

    for proj_section in xml_root.findall('.//section[@label="Research Funding History"]'):
        title = extract_field_value(proj_section, 'Funding Title')
        if not title:
            continue

        ext_id = get_record_id(proj_section, [title])
        seen_external_ids.add(ext_id)

        start_date = parse_funding_date(extract_field_value(proj_section, 'Funding Start Date'))
        end_date   = parse_funding_date(extract_field_value(proj_section, 'Funding End Date'))

        status_str = extract_field_value(proj_section, 'Funding Status') or ''
        s = status_str.lower()
        if 'award' in s or 'funded' in s:                                         status = 'awarded'
        elif 'completed' in s or 'closed' in s:                                   status = 'completed'
        elif 'rejected' in s or 'unsuccessful' in s or 'declined' in s:           status = 'rejected'
        elif 'review' in s or 'submitted' in s or 'pending' in s or 'under' in s: status = 'submitted'
        else:                                                                      status = 'pending'

        role         = map_funding_role_to_choice(extract_field_value(proj_section, 'Funding Role'))
        funding_type = extract_field_value(proj_section, 'Funding Type')

        description = None
        desc_field  = proj_section.find('field[@label="Project Description"]')
        if desc_field is not None:
            description = extract_bilingual_value(desc_field)

        funding_org = program_name = None
        currency = 'CAD'
        total_funding_sum = funding_received_sum = 0.0

        for funding_src in proj_section.findall('section[@label="Funding Sources"]'):
            org_main  = extract_field_value(funding_src, 'Funding Organization')
            org_other = extract_field_value(funding_src, 'Other Funding Organization')
            org = (
                f"{org_main} / {org_other}" if (org_main and org_other)
                else (org_main or org_other)
            )
            if not funding_org and org:
                funding_org  = org
                program_name = extract_field_value(funding_src, 'Program Name')
                currency_str = (extract_field_value(funding_src, 'Currency of Total Funding') or '').lower()
                currency     = 'USD' if 'united states' in currency_str else 'CAD'

            total_str    = extract_field_value(funding_src, 'Total Funding')
            received_str = extract_field_value(funding_src, 'Portion of Funding Received')

            try:
                total_funding_sum += float(total_str) if total_str else 0
            except Exception as e:
                logger.warning(f"[CCV] Failed to parse total funding for '{title}': {total_str!r} | {e}")

            try:
                funding_received_sum += float(received_str) if received_str else 0
            except Exception as e:
                logger.warning(f"[CCV] Failed to parse funding received for '{title}': {received_str!r} | {e}")

        total_funding    = total_funding_sum    or None
        funding_received = funding_received_sum or None

        ccv_fields = dict(
            description = description,
            ccv_active  = True,
            source      = 'ccv',
            currency    = currency,
        )

        first_create_only = dict(
            title                = title[:500],
            status               = status,
            role                 = role,
            funding_type         = funding_type,
            funding_organization = funding_org or '',
            program_name         = program_name or '',
            total_funding        = total_funding,
            funding_received     = funding_received,
            start_date           = start_date,
            end_date             = end_date,
        )

        existing = Project.all_objects.filter(
            researcher=researcher, external_id=ext_id, source='ccv',
        ).first()

        if not existing:
            existing = Project.all_objects.filter(
                researcher=researcher, title__iexact=title, source='manual',
            ).first()
            if existing:
                existing.source      = 'ccv'
                existing.external_id = ext_id
                logger.info(f"[CCV] Manual project '{title}' claimed by CCV import")

        if existing:
            if existing.is_deleted:
                continue
            for k, v in ccv_fields.items():
                setattr(existing, k, v)
            if not existing.manually_overridden:
                for k, v in first_create_only.items():
                    setattr(existing, k, v)
            existing.ccv_active = True
            existing.save()
            project = existing
            count_updated += 1
        else:
            project = Project.objects.create(
                researcher=researcher, external_id=ext_id,
                **ccv_fields, **first_create_only,
            )
            count_created += 1

        project.team_members.filter(is_academic_collaborator=True).delete()

        for inv_section in proj_section.findall('section[@label="Other Investigators"]'):
            inv_name = extract_field_value(inv_section, 'Investigator Name')
            if inv_name:
                ProjectMember.objects.create(
                    project                  = project,
                    name                     = inv_name,
                    role                     = map_funding_role_to_choice(
                        extract_field_value(inv_section, 'Role')
                    ),
                    is_academic_collaborator = True,
                    partner_type             = 'academic',
                )

    Project.objects.filter(
        researcher=researcher, source='ccv', ccv_active=True,
    ).exclude(external_id__in=seen_external_ids).update(ccv_active=False)

    return count_created + count_updated


# ─────────────────────────────────────────────
# parse_xml_supervision
# ─────────────────────────────────────────────

def parse_xml_supervision(researcher, xml_root):
    from config.models import SupervisionRecord

    seen_ids = set()
    count_created = count_updated = 0

    existing_records = {
        r.external_id: r
        for r in SupervisionRecord.objects.filter(researcher=researcher)
    }

    for sup_section in xml_root.findall('.//section[@label="Student/Postdoctoral Supervision"]'):
        student_name = (extract_field_value(sup_section, 'Student Name') or '').strip()
        if not student_name:
            continue

        ext_id = get_record_id(sup_section, [student_name, str(researcher.id)])
        seen_ids.add(ext_id)

        degree_raw   = extract_field_value(sup_section, 'Degree Type or Postdoctoral Status') or ''
        degree_clean = degree_raw.lower().replace("\u2019", "'").replace("'", "'").strip()

        if 'bachelor' in degree_clean:                                      degree_type = 'bachelors'
        elif 'non-thesis' in degree_clean or 'non thesis' in degree_clean: degree_type = 'masters_non_thesis'
        elif 'master' in degree_clean:                                      degree_type = 'masters_thesis'
        elif 'doctor' in degree_clean or 'phd' in degree_clean:            degree_type = 'doctorate'
        elif 'postdoc' in degree_clean or 'post-doc' in degree_clean:      degree_type = 'postdoc'
        elif 'research associate' in degree_clean:                          degree_type = 'research_associate'
        else:                                                               degree_type = None

        status_raw   = extract_field_value(sup_section, 'Student Degree Status') or ''
        status_clean = status_raw.lower()
        if 'completed' in status_clean:
            status = 'completed'
        elif any(x in status_clean for x in ['progress', 'ongoing', 'current', 'enrolled']):
            status = 'in_progress'
        else:
            status = None

        role        = (extract_field_value(sup_section, 'Supervision Role') or '').strip()
        institution = (extract_field_value(sup_section, 'Student Institution') or '').strip()
        thesis      = (extract_field_value(sup_section, 'Thesis/Project Title') or '').strip()
        position    = (extract_field_value(sup_section, 'Present Position') or '').strip()
        org         = (extract_field_value(sup_section, 'Present Organization') or '').strip()
        residency   = (extract_field_value(sup_section, 'Student Canadian Residency Status') or '').strip()

        start_date   = parse_funding_date(extract_field_value(sup_section, 'Supervision Start Date'))
        end_date     = parse_funding_date(extract_field_value(sup_section, 'Supervision End Date'))
        degree_start = parse_funding_date(extract_field_value(sup_section, 'Student Degree Start Date'))
        degree_end   = parse_funding_date(extract_field_value(sup_section, 'Student Degree Received Date'))
        expected     = parse_funding_date(extract_field_value(sup_section, 'Student Degree Expected Date'))

        ccv_fields = dict(
            student_name      = student_name,
            institution       = institution,
            degree_type       = degree_type,
            supervision_role  = role,
            status            = status,
            start_date        = start_date,
            end_date          = end_date,
            degree_start_date = degree_start,
            degree_end_date   = degree_end,
            thesis_title      = thesis,
            present_position  = position,
            present_org       = org,
            residency_status  = residency,
        )

        existing = existing_records.get(ext_id)

        if existing:
            for k, v in ccv_fields.items():
                setattr(existing, k, v)
            if not existing.manually_overridden:
                existing.expected_date = expected
            existing.save()
            try_link_student(existing)
            count_updated += 1
        else:
            new_record = SupervisionRecord.objects.create(
                researcher=researcher, external_id=ext_id,
                **ccv_fields, expected_date=expected,
            )
            try_link_student(new_record)
            count_created += 1

    SupervisionRecord.objects.filter(
        researcher=researcher,
    ).exclude(external_id__in=seen_ids).filter(
        manually_overridden=False
    ).delete()

    return count_created + count_updated


# ─────────────────────────────────────────────
# parse_xml_student_profile
# ─────────────────────────────────────────────

def parse_xml_student_profile(user, xml_root):
    from config.models import StudentProfile, ResearcherProfile

    profile, _ = StudentProfile.objects.get_or_create(user=user, defaults={})

    if not profile.manually_overridden:
        for edu_section in xml_root.findall('.//section[@label="Education"]'):
            latest_degree_section = None
            latest_date = None

            for degree_section in edu_section.findall('.//section[@label="Degrees"]'):
                received = degree_section.find('field[@label="Degree Received Date"]')
                expected = degree_section.find('field[@label="Degree Expected Date"]')
                start    = degree_section.find('field[@label="Degree Start Date"]')

                if received is not None:   date_field = received
                elif expected is not None: date_field = expected
                else:                      date_field = start

                date_val = ''
                if date_field is not None:
                    date_val = (date_field.findtext('value') or '').strip()

                try:
                    parts = date_val.replace('/', '-').split('-')
                    year  = int(parts[0])
                    month = int(parts[1]) if len(parts) > 1 else 1
                    d     = date(year, month, 1)
                except (ValueError, IndexError):
                    d = None

                if d is not None:
                    if latest_date is None or d > latest_date:
                        latest_date           = d
                        latest_degree_section = degree_section
                else:
                    latest_degree_section = degree_section

            if latest_degree_section is None:
                continue

            degree_type_field = latest_degree_section.find('field[@label="Degree Type"]')
            if degree_type_field is not None:
                val = (
                    degree_type_field.findtext('lov') or
                    degree_type_field.findtext('value') or
                    degree_type_field.findtext('lov/text') or ''
                ).strip().lower()

                if 'bachelor' in val or 'bsc' in val:   profile.degree_level = 'undergrad'
                elif 'master' in val or 'msc' in val:   profile.degree_level = 'msc'
                elif 'phd' in val or 'doctor' in val:   profile.degree_level = 'phd'
                elif 'postdoc' in val:                  profile.degree_level = 'pdf'

            spec_field = latest_degree_section.find('field[@label="Specialization"]')
            dept_field = latest_degree_section.find('field[@label="Department"]')

            if spec_field is not None:
                val = spec_field.findtext('value', '').strip()
                if val:
                    profile.department = val

            if not profile.department and dept_field is not None:
                val = dept_field.findtext('value', '').strip()
                if val:
                    profile.department = val

            if not profile.department:
                for field in xml_root.findall('.//field[@label="Department"]'):
                    val = field.findtext('value')
                    if val and val.strip():
                        profile.department = val.strip()
                        break

            if not profile.department:
                degree_name_field = latest_degree_section.find('field[@label="Degree Name"]')
                if degree_name_field is not None:
                    val = degree_name_field.findtext('value', '').strip()
                    if val and ' of ' in val.lower():
                        profile.department = val.split(' of ', 1)[-1].strip()

            thesis_field = latest_degree_section.find('field[@label="Thesis Title"]')
            if thesis_field is not None:
                val = thesis_field.findtext('value', '').strip()
                if val:
                    profile.thesis_title = val

            for field_label, attr in [
                ('Degree Start Date',    'start_date'),
                ('Degree Expected Date', 'expected_end_date'),
                ('Degree Received Date', 'graduation_date'),
            ]:
                f = latest_degree_section.find(f'field[@label="{field_label}"]')
                if f is not None:
                    val = (f.findtext('value') or '').strip()
                    if val:
                        try:
                            parts = val.replace('/', '-').split('-')
                            year  = int(parts[0])
                            month = int(parts[1]) if len(parts) > 1 else 1
                            setattr(profile, attr, date(year, month, 1))
                        except (ValueError, IndexError):
                            pass

            break

    if not profile.supervisor:
        for edu_section in xml_root.findall('.//section[@label="Education"]'):
            for degree_section in edu_section.findall('.//section[@label="Degrees"]'):
                for sup_section in degree_section.findall('.//section[@label="Supervisors"]'):
                    sup_name = (extract_field_value(sup_section, 'Supervisor Name') or '').strip()
                    if not sup_name:
                        continue

                    clean  = re.sub(r'[^a-zA-Z\s]', '', sup_name.lower()).strip()
                    parts  = clean.split()
                    if len(parts) < 2:
                        continue

                    first, last = parts[0], parts[-1]

                    matches = list(ResearcherProfile.objects.filter(
                        user__first_name__iexact=first,
                        user__last_name__iexact=last,
                        user__user_type='researcher',
                    )[:2])

                    if len(matches) == 1:
                        profile.supervisor = matches[0]
                        break

                    reversed_matches = list(ResearcherProfile.objects.filter(
                        user__first_name__iexact=last,
                        user__last_name__iexact=first,
                        user__user_type='researcher',
                    )[:2])

                    if len(reversed_matches) == 1:
                        profile.supervisor = reversed_matches[0]
                        break

                if profile.supervisor:
                    break
            if profile.supervisor:
                break

    researcher = get_student_researcher_proxy(user)

    with transaction.atomic():
        profile.save()
        pub_count   = parse_xml_publications(researcher, xml_root)
        act_count   = parse_xml_activities(researcher, xml_root)
        recog_count = parse_xml_recognitions(researcher, xml_root)
        edu_count   = parse_xml_education(researcher, xml_root)

    return {
        'degree_level': profile.degree_level,
        'department':   profile.department,
        'publications': pub_count,
        'activities':   act_count,
        'recognitions': recog_count,
        'education':    edu_count,
    }


# ─────────────────────────────────────────────
# process_xml_file  (admin bulk upload handler)
# ─────────────────────────────────────────────

def process_xml_file(file_obj):
    from defusedxml import ElementTree as ET

    try:
        tree     = ET.parse(file_obj)
        xml_root = tree.getroot()
    except ET.ParseError as e:
        return {'filename': file_obj.name, 'success': False, 'error': f'Invalid XML: {e}'}

    try:
        if "generic-cv" not in xml_root.tag:
            return {'filename': file_obj.name, 'success': False, 'error': 'Invalid CCV XML format'}

        is_valid, error = validate_ccv_structure(xml_root)
        if not is_valid:
            return {'filename': file_obj.name, 'success': False, 'error': error}

        ident_data = {}
        ident_section = xml_root.find('.//section[@label="Identification"]')
        if ident_section is not None:
            ident_data = {
                'first_name':       extract_field_value(ident_section, 'First Name'),
                'last_name':        extract_field_value(ident_section, 'Family Name'),
                'title':            extract_field_value(ident_section, 'Title'),
                'sex':              extract_field_value(ident_section, 'Sex'),
                'language':         extract_field_value(ident_section, 'Correspondence Language'),
                'residency_status': extract_field_value(ident_section, 'Canadian Residency Status'),
            }

        first_name = ident_data.get('first_name')
        last_name  = ident_data.get('last_name')

        if not first_name or not last_name:
            return {'filename': file_obj.name, 'success': False,
                    'error': 'Could not find researcher name in XML'}

        email = None
        email_section = xml_root.find('.//section[@label="Email"]')
        if email_section is not None:
            email = extract_field_value(email_section, 'Email Address')

        if not email:
            return {'filename': file_obj.name, 'success': False,
                    'error': f'No email found for {first_name} {last_name}.'}

        org_section  = xml_root.find('.//section[@label="Organization"]')
        organization = extract_field_value(org_section, "Organization") if org_section is not None else ""

        try:
            email = email.strip().lower()
            user  = CustomUser.objects.get(email=email)

            if user.user_type != 'researcher':
                return {'filename': file_obj.name, 'success': False,
                        'error': f'{email} exists but is not a researcher. Admin approval required.'}

            if user.approval_status == 'rejected':
                return {'filename': file_obj.name, 'success': False,
                        'error': f'{first_name} {last_name} ({email}) has been rejected. Cannot import data.'}

            if user.approval_status == 'pending':
                user.first_name = first_name
                user.last_name  = last_name
                user.save()
                ResearcherProfile.objects.get_or_create(user=user, defaults={'research_interests': ''})
                return {
                    'filename': file_obj.name, 'success': True,
                    'researcher': f"{first_name} {last_name}", 'email': email,
                    'education': 0, 'funding': 0, 'recognitions': 0,
                    'publications': 0, 'activities': 0, 'projects': 0,
                    'supervisor_count': 0, 'total_records': 0,
                    'note': 'Pending approval — data will import after admin approves.',
                }

        except CustomUser.DoesNotExist:
            PENDING_CAP = 20
            if CustomUser.objects.filter(approval_status='pending').count() >= PENDING_CAP:
                return {'filename': file_obj.name, 'success': False,
                        'error': 'Too many pending accounts. Approve or reject existing users before uploading more.'}

            username = f"{first_name.lower()}.{last_name.lower()}.{uuid.uuid4().hex[:6]}".replace(' ', '')
            user = CustomUser.objects.create_user(
                email=email, username=username,
                first_name=first_name, last_name=last_name,
                user_type='researcher', approval_status='pending',
                organization=organization, password=secrets.token_urlsafe(16),
            )
            user.save()
            ResearcherProfile.objects.get_or_create(user=user, defaults={'research_interests': ''})

            for admin_user in CustomUser.objects.filter(user_type='admin'):
                StudentNotification.objects.create(
                    user=admin_user,
                    message=f'{first_name} {last_name} ({email}) has been uploaded via CCV and is awaiting approval.',
                )

            return {
                'filename': file_obj.name, 'success': True,
                'researcher': f"{first_name} {last_name}", 'email': email,
                'education': 0, 'funding': 0, 'recognitions': 0,
                'publications': 0, 'activities': 0, 'projects': 0,
                'supervisor_count': 0, 'total_records': 0,
                'note': 'New user created as pending — data will import after admin approves.',
            }

        user.first_name = first_name
        user.last_name  = last_name
        user.save()

        researcher, _ = ResearcherProfile.objects.get_or_create(
            user=user, defaults={'research_interests': ''}
        )
        researcher.title            = ident_data.get('title') or ''
        researcher.sex              = ident_data.get('sex') or ''
        researcher.language         = ident_data.get('language') or ''
        researcher.residency_status = ident_data.get('residency_status') or ''

        submission = xml_root.find('.//submission')
        if submission is not None:
            researcher.ccv_identifier = submission.get('ccvIdentifier') or ''
        researcher.save()

        try:
            with transaction.atomic():
                education_count   = parse_xml_education(researcher, xml_root)
                funding_count     = parse_xml_funding(researcher, xml_root)
                recognition_count = parse_xml_recognitions(researcher, xml_root)
                publication_count = parse_xml_publications(researcher, xml_root)
                activity_count    = parse_xml_activities(researcher, xml_root)
                project_count     = parse_xml_projects(researcher, xml_root)
                supervision_count = parse_xml_supervision(researcher, xml_root)
        except Exception as e:
            return {'filename': file_obj.name, 'success': False,
                    'error': f'Data import failed and was rolled back: {e}'}

        return {
            'filename':         file_obj.name,
            'success':          True,
            'researcher':       f"{first_name} {last_name}",
            'email':            email,
            'education':        education_count,
            'funding':          funding_count,
            'recognitions':     recognition_count,
            'publications':     publication_count,
            'activities':       activity_count,
            'projects':         project_count,
            'supervisor_count': supervision_count,
            'total_records': (
                education_count + funding_count + recognition_count +
                publication_count + activity_count + project_count
            ),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'filename': file_obj.name, 'success': False, 'error': f'Processing error: {e}'}