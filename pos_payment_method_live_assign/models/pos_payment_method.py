# Copyright 2026 Saad Elbahi
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError

from .pos_config import resolve_target_m2m_ids


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _is_write_forbidden(self, fields_set):
        if self.env.context.get("bypass_payment_method_ids_forbidden_change"):
            whitelisted = {"sequence", "config_ids"}
            return bool(fields_set - whitelisted and self.open_session_ids)
        return super()._is_write_forbidden(fields_set)

    def _validate_live_config_changes(self, raw_cmds):
        added_configs_by_pm = {}
        for pm in self:
            current_cfg_ids = set(pm.config_ids.ids)
            target_cfg_ids = resolve_target_m2m_ids(current_cfg_ids, raw_cmds)
            removed_cfg_ids = current_cfg_ids - target_cfg_ids
            if removed_cfg_ids:
                removed_open = (
                    self.env["pos.config"]
                    .browse(list(removed_cfg_ids))
                    .filtered("has_active_session")
                )
                if removed_open:
                    raise UserError(
                        _(
                            "Cannot unlink payment method (%(method)s) from POS with "
                            "open sessions: %(pos)s",
                            method=pm.display_name,
                            pos=", ".join(removed_open.mapped("display_name")),
                        )
                    )
            added_cfg_ids = target_cfg_ids - current_cfg_ids
            if added_cfg_ids:
                added_cfgs = self.env["pos.config"].browse(list(added_cfg_ids))
                if added_cfgs.filtered("has_active_session"):
                    added_cfgs[:1]._validate_safe_live_payment_methods(pm)
                added_configs_by_pm[pm.id] = added_cfgs
        return added_configs_by_pm

    def write(self, vals):
        if (
            set(vals.keys()) <= {"config_ids", "sequence"}
            and "config_ids" in vals
            and not self.env.context.get("bypass_payment_method_ids_forbidden_change")
        ):
            added_configs_by_pm = self._validate_live_config_changes(vals["config_ids"])
            res = super(
                PosPaymentMethod,
                self.with_context(bypass_payment_method_ids_forbidden_change=True),
            ).write(vals)
            for pm in self:
                for cfg in added_configs_by_pm.get(pm.id, self.env["pos.config"]):
                    cfg._notify_live_payment_methods_added(pm)
            return res
        return super().write(vals)

    def action_open_live_assign_wizard(self):
        self.ensure_one()
        if self.is_cash_count or (self.journal_id and self.journal_id.type == "cash"):
            raise UserError(
                _(
                    "Cash payment method (%s) cannot be assigned during open sessions.",
                    self.display_name,
                )
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Assign Payment Method to POS"),
            "res_model": "pos.live.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_payment_method_id": self.id,
            },
        }
