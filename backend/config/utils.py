# config/utils.py

# Fields hidden from students across all views.
# Apply mask_financial_fields() to any dict returned to the frontend
# that may be accessed by students (e.g. tagged project views).
FINANCIAL_FIELDS = [
    'total_funding',       # Project.total_funding
    'funding_received',    # Project.funding_received  
    'funding_kept_by_unb', # Project.funding_kept_by_unb
    'amount',              # Funding.amount
    'amount_to_ibme',      # Funding.amount_to_ibme
]

def mask_financial_fields(data, user):
    """
    Strip financial fields from a dict or list of dicts
    if the user is a student.
    
    Works on:
    - a single dict (e.g. from api_get_project)
    - a list of dicts
    """
    if user.user_type != 'student':
        return data

    if isinstance(data, list):
        return [_mask_single(item) for item in data]
    
    if isinstance(data, dict):
        return _mask_single(data)
    
    return data


def _mask_single(item):
    masked = item.copy()
    for field in FINANCIAL_FIELDS:
        if field in masked:
            masked[field] = "Restricted"
    return masked


def log_action(request, action, target=None, summary=None, details=None):

    from .models import AuditLog
    ip = None
    if request:
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        )
    AuditLog.objects.create(
        user        = request.user if request and request.user.is_authenticated else None,
        action      = action,
        target_type = target.__class__.__name__ if target else None,
        target_id   = target.pk if target else None,
        summary     = summary or '',
        details     = details or {},
        ip_address  = ip,
    )


def generate_project_summary(project):
    parts    = []
    role_map = {
        'pi':     'Principal Investigator-led',
        'co_pi':  'Co-Investigator',
        'pa':     'Principal Applicant-led',
        'co_app': 'Co-applicant',
        'other':  'Team member',
    }
    role_str     = role_map.get(project.role, '') if project.role else ''
    funding_type = (project.funding_type or 'project').lower()
    opening      = f"{role_str} {funding_type}".strip() if role_str else funding_type.capitalize()
    parts.append(opening)

    if project.funding_organization:
        parts[-1] += f" funded by {project.funding_organization}"

    if project.program_name:
        parts[-1] += f" under the {project.program_name} program"

    if project.start_date and project.end_date:
        parts.append(f"running from {project.start_date} to {project.end_date}")
    elif project.start_date:
        parts.append(f"starting {project.start_date}")

    if project.total_funding:
        parts.append(f"with total funding of ${int(project.total_funding):,}")

    # Use len() to avoid bypassing prefetch cache
    team_count = len(project.team_members.all())
    if team_count > 0:
        parts.append(f"involving a team of {team_count + 1}")

    if not parts:
        return f"Research project: {project.title}."

    summary = ", ".join(parts) + "."
    return summary[0].upper() + summary[1:]

