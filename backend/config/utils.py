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