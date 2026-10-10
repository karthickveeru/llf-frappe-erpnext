import io

import frappe
from frappe.utils import flt
from erpnext.assets.doctype.asset.asset import Asset

try:
    import qrcode
    HAS_QR = True
except Exception:
    HAS_QR = False


class LLFAsset(Asset):

    def validate(self):
        self._set_existing_asset_defaults()
        self._sync_value_after_depreciation()
        super().validate()
        if not self.llf_asset_tag:
            self._generate_asset_tag()

    def before_submit(self):
        self._sync_value_after_depreciation()

    def on_submit(self):
        super().on_submit()
        if self.llf_asset_tag and HAS_QR:
            self._attach_qr_code()

    def validate_asset_values(self):
        if flt(self.get("invoice_value")):
            self.gross_purchase_amount = flt(self.invoice_value)

        original_gpa = self.gross_purchase_amount
        if not flt(self.gross_purchase_amount):
            self.gross_purchase_amount = 1
        super().validate_asset_values()
        if not flt(original_gpa):
            self.gross_purchase_amount = 0

    def make_asset_movement(self):
        if not self.location:
            return
        super().make_asset_movement()

    def _sync_value_after_depreciation(self):
        ref = flt(self.get("llf_asset_value")) or flt(self.get("invoice_value")) or flt(self.get("gross_purchase_amount"))
        if ref:
            self.value_after_depreciation = ref

    def _set_existing_asset_defaults(self):
        if not self.purchase_receipt and not self.purchase_invoice:
            self.is_existing_asset = 1

    def _generate_asset_tag(self):
        if not (self.item_code and self.project and self.financial_year):
            return
        project_name = (
            frappe.db.get_value("Project", self.project, "project_name") or self.project
        )
        sequence = _next_sequence(self.item_code)
        self.llf_asset_tag = (
            f"LLF/{self.item_code}/{project_name}/{self.financial_year}/{sequence:03d}"
        )

    def _attach_qr_code(self):
        filename = "QR-{}.png".format(self.llf_asset_tag.replace("/", "-"))

        existing = frappe.db.exists("File", {
            "attached_to_doctype": "Asset",
            "attached_to_name": self.name,
            "file_name": filename,
        })
        if existing:
            return

        project_name = (
            frappe.db.get_value("Project", self.project, "project_name") or self.project
        ) if self.project else ""

        qr_data = "\n".join(filter(None, [
            f"ID: {self.name}",
            f"Tag: {self.llf_asset_tag}",
            f"Project: {project_name}" if project_name else "",
            f"S/N: {self.serial_no}" if self.get("serial_no") else "",
        ]))

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "attached_to_doctype": "Asset",
            "attached_to_name": self.name,
            "content": buf.read(),
            "is_private": 0,
        }).insert(ignore_permissions=True)


def _next_sequence(item_code):
    return (
        frappe.db.count("Asset", {"item_code": item_code, "llf_asset_tag": ["is", "set"]}) + 1
    )
