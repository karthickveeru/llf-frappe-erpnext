from erpnext.assets.doctype.asset_movement.asset_movement import AssetMovement


class LLFAssetMovement(AssetMovement):
    def validate_location(self, d):
        if self.purpose == "Receipt":
            return
        super().validate_location(d)
