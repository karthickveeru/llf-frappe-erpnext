app_name = 'llf_erpnext'
app_title = 'LLF ERPNext'
app_publisher = 'Learning Links Foundation'
app_description = 'Asset management customizations for Learning Links Foundation'
app_email = 'ajay.kumar@learninglinksindia.org'
app_license = 'MIT'

fixtures = [
    {
        'dt': 'Custom Field',
        'filters': [['dt', '=', 'Asset']]
    },
    {
        'dt': 'Property Setter',
        'filters': [['doc_type', '=', 'Asset']]
    },
    {
        'dt': 'Print Format',
        'filters': [['doc_type', '=', 'Asset'], ['custom_format', '=', 1]]
    },
    {
        'dt': 'DocType',
        'filters': [['name', '=', 'LLF Asset Service History']]
    },
]

override_doctype_class = {
    'Asset': 'llf_erpnext.overrides.asset.LLFAsset',
    'Asset Movement': 'llf_erpnext.overrides.asset_movement.LLFAssetMovement',
}

override_whitelisted_methods = {
    "frappe.integrations.oauth2_logins.login_via_office365": "llf_erpnext.overrides.oauth.login_via_office365"
}
