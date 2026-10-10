import json
import traceback
import uuid
import frappe
from frappe.utils.oauth import get_info_via_oauth, login_oauth_user


GROUP_ROLE_MAP = {
    "9c7a85de-7f89-4a90-bd6d-2bbb0e5cf362": "LLF Project Manager",
    "8a0bf07b-e6a8-415c-a243-f91c39aebf24": "System Manager",
    "943f526f-9485-474b-9aa4-ded1142e59db": "LLF Project Representative",
    "ec26e3cd-d78d-4ca1-bf5c-23db69fc2fb3": "LLF Senior Leadership",
}


def _decoder(b):
    return json.loads(bytes(b).decode("utf-8"))


@frappe.whitelist(allow_guest=True)
def login_via_office365(code: str, state: str):
    info = get_info_via_oauth("office_365", code, _decoder, id_token=True)

    with open('/tmp/oauth_debug.json', 'w') as f:
        json.dump(info, f, default=str, indent=2)

    if not info.get("email") and not info.get("unique_name"):
        info["email"] = info.get("preferred_username") or info.get("upn")

    if not info.get("first_name"):
        name_parts = (info.get("name") or "").split()
        info["first_name"] = info.get("given_name") or (name_parts[0] if name_parts else "User")
    if not info.get("last_name"):
        info["last_name"] = info.get("family_name") or ""

    login_oauth_user(info, provider="office_365", state=state)

    try:
        _sync_roles(info)
    except Exception:
        with open('/tmp/sync_error.txt', 'w') as f:
            f.write(traceback.format_exc())


def _sync_roles(info):
    email = info.get("email") or info.get("preferred_username")
    if not email:
        return
    # Ensure desk access for LLF users
    frappe.db.sql(
        "UPDATE `tabUser` SET user_type='System User' WHERE name=%s AND user_type='Website User'",
        (email,)
    )

    token_groups = info.get("groups") or []
    desired_roles = {GROUP_ROLE_MAP[g] for g in token_groups if g in GROUP_ROLE_MAP}
    llf_roles = list(GROUP_ROLE_MAP.values())

    if llf_roles:
        placeholders = ",".join(["%s"] * len(llf_roles))
        keep_placeholders = ",".join(["%s"] * len(desired_roles)) if desired_roles else None
        if keep_placeholders:
            frappe.db.sql(
                "DELETE FROM `tabHas Role` WHERE parent=%s AND role IN ({}) AND role NOT IN ({})".format(
                    placeholders, keep_placeholders
                ),
                tuple([email] + llf_roles + list(desired_roles))
            )
        else:
            frappe.db.sql(
                "DELETE FROM `tabHas Role` WHERE parent=%s AND role IN ({})".format(placeholders),
                tuple([email] + llf_roles)
            )

    for role in desired_roles:
        exists = frappe.db.sql(
            "SELECT name FROM `tabHas Role` WHERE parent=%s AND role=%s", (email, role)
        )
        if not exists:
            frappe.db.sql("""
                INSERT INTO `tabHas Role` (name, parent, parenttype, parentfield, role, creation, modified, modified_by, owner)
                VALUES (%s, %s, 'User', 'roles', %s, NOW(), NOW(), 'Administrator', 'Administrator')
            """, (str(uuid.uuid4())[:10], email, role))

    frappe.db.sql("COMMIT")

    with open('/tmp/sync_done.txt', 'w') as f:
        f.write("Synced roles for {}: {}".format(email, desired_roles))
