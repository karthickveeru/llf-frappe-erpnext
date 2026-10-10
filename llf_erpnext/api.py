import frappe
import base64
import io

try:
    import qrcode
    HAS_QR = True
except Exception:
    HAS_QR = False

from frappe.utils.pdf import get_pdf


def _qr_b64(text):
    if not HAS_QR or not text:
        return ''
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=3, border=1)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def _tag_card(a):
    qr_b64 = _qr_b64(a.get('llf_asset_tag') or a.get('name'))
    qr_html = (
        '<img src="data:image/png;base64,' + qr_b64 + '" '
        'style="width:60px;height:60px;display:block;flex-shrink:0;" />'
    ) if qr_b64 else '<div style="width:60px;height:60px;background:#eee;flex-shrink:0;"></div>'

    tag      = a.get('llf_asset_tag') or ''
    name     = a.get('asset_name') or a.get('name') or ''
    serial   = a.get('serial_number') or ''
    project  = a.get('project_allocated_to') or ''
    location = a.get('location') or ''
    asset_id = a.get('name') or ''

    rows = (
        '<tr><td style="color:#555;white-space:nowrap;padding-right:4px;">ID</td>'
        '<td style="word-break:break-all;">' + asset_id + '</td></tr>'
        + ('<tr><td style="color:#555;white-space:nowrap;padding-right:4px;">S/N</td>'
           '<td>' + serial + '</td></tr>' if serial else '')
        + ('<tr><td style="color:#555;white-space:nowrap;padding-right:4px;">Project</td>'
           '<td style="word-break:break-word;">' + project + '</td></tr>' if project else '')
        + ('<tr><td style="color:#555;white-space:nowrap;padding-right:4px;">Location</td>'
           '<td>' + location + '</td></tr>' if location else '')
    )

    return (
        '<div style="border:1px solid #aaa;border-radius:3px;padding:6px;'
        'box-sizing:border-box;font-family:Arial,sans-serif;font-size:8px;'
        'page-break-inside:avoid;overflow:hidden;">'
        # top row: QR + tag number + name
        '<div style="display:flex;align-items:flex-start;gap:6px;margin-bottom:4px;">'
        + qr_html +
        '<div style="overflow:hidden;">'
        '<div style="font-size:7px;color:#777;font-weight:bold;letter-spacing:.5px;">LLF ASSET TAG</div>'
        '<div style="font-size:8px;font-weight:bold;word-break:break-all;line-height:1.2;">' + tag + '</div>'
        '<div style="font-size:9px;font-weight:bold;margin-top:2px;">' + name + '</div>'
        '</div>'
        '</div>'
        # detail rows
        '<table style="width:100%;border-collapse:collapse;font-size:7.5px;line-height:1.3;">'
        + rows +
        '</table>'
        '</div>'
    )


@frappe.whitelist()
def download_project_tags(project=None):
    filters = {'docstatus': 1}
    if project and project != '__all__':
        filters['project_allocated_to'] = project

    if project and project != '__all__':
        assets = frappe.db.sql(
            """SELECT name, asset_name, llf_asset_tag, serial_number,
                      project_allocated_to, location
               FROM `tabAsset`
               WHERE docstatus = 1 AND project_allocated_to = %s
               ORDER BY name""",
            project, as_dict=True
        )
    else:
        assets = frappe.db.sql(
            """SELECT name, asset_name, llf_asset_tag, serial_number,
                      project_allocated_to, location
               FROM `tabAsset`
               WHERE docstatus = 1
               ORDER BY name""",
            as_dict=True
        )

    assets = sorted(assets, key=lambda a: a.get('llf_asset_tag') or '')

    if not assets:
        frappe.throw('No submitted assets found' + (' for project: ' + project if project else ''))

    cards_html = ''.join(
        '<div style="width:50%;display:inline-block;vertical-align:top;'
        'padding:3px;box-sizing:border-box;">'
        + _tag_card(a) +
        '</div>'
        for a in assets
    )

    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        'body{margin:0;padding:0;font-family:Arial,sans-serif;}'
        '@page{size:A4;margin:8mm;}'
        '</style>'
        '</head><body>'
        '<div style="font-family:Arial,sans-serif;font-size:10px;font-weight:bold;'
        'margin-bottom:6px;border-bottom:2px solid #333;padding-bottom:3px;">'
        'LLF Asset Tags &mdash; ' + (project or 'All Projects') +
        ' (' + str(len(assets)) + ' assets)'
        '</div>'
        '<div style="font-size:0;">' + cards_html + '</div>'
        '</body></html>'
    )

    options = {
        'page-size': 'A4',
        'margin-top': '8mm',
        'margin-bottom': '8mm',
        'margin-left': '8mm',
        'margin-right': '8mm',
        'disable-smart-shrinking': '',
    }

    pdf = get_pdf(html, options=options)

    fname = 'LLF_Asset_Tags_' + (project or 'All').replace(' ', '_') + '.pdf'
    frappe.response.filename = fname
    frappe.response.filecontent = pdf
    frappe.response.type = 'download'
