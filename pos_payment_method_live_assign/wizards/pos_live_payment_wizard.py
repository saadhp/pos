# Copyright 2026 Saad Elbahi
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PosLivePaymentWizard(models.TransientModel):
    _name = "pos.live.payment.wizard"
    _description = "POS Live Payment Method Assignment"

    payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Payment Method",
        required=True,
        domain="[('is_cash_count', '=', False)]",
    )
    company_id = fields.Many2one(related="payment_method_id.company_id", readonly=True)
    existing_config_ids = fields.Many2many(
        "pos.config",
        compute="_compute_existing_configs",
        string="Assigned POS",
    )
    target_config_ids = fields.Many2many(
        "pos.config",
        "pos_live_pm_wiz_config_rel",
        "wizard_id",
        "config_id",
        string="POS to Assign",
        domain=(
            "[('company_id', '=', company_id), ('id', 'not in', existing_config_ids)]"
        ),
    )
    open_sessions_summary = fields.Char(
        compute="_compute_open_sessions_summary",
        string="Open Sessions",
    )

    @api.depends("payment_method_id")
    def _compute_existing_configs(self):
        for wiz in self:
            wiz.existing_config_ids = wiz.payment_method_id.config_ids

    @api.onchange("payment_method_id")
    def _onchange_payment_method_id(self):
        if self.payment_method_id:
            remaining = self.env["pos.config"].search(
                [
                    ("company_id", "=", self.payment_method_id.company_id.id),
                    ("id", "not in", self.payment_method_id.config_ids.ids),
                ]
            )
            self.target_config_ids = remaining

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        pm_id = res.get("payment_method_id") or self.env.context.get(
            "default_payment_method_id"
        )
        if pm_id and "target_config_ids" in fields_list:
            pm = self.env["pos.payment.method"].browse(pm_id)
            remaining = self.env["pos.config"].search(
                [
                    ("company_id", "=", pm.company_id.id),
                    ("id", "not in", pm.config_ids.ids),
                ]
            )
            res["target_config_ids"] = [Command.set(remaining.ids)]
        return res

    @api.depends("target_config_ids")
    def _compute_open_sessions_summary(self):
        for wiz in self:
            if not wiz.target_config_ids:
                wiz.open_sessions_summary = _("No additional POS selected.")
                continue
            open_cnt = len(wiz.target_config_ids.filtered("has_active_session"))
            closed_cnt = len(wiz.target_config_ids) - open_cnt
            wiz.open_sessions_summary = _(
                "Selected POS: %(total)s (Open sessions: %(open)s, Closed: %(closed)s)",
                total=len(wiz.target_config_ids),
                open=open_cnt,
                closed=closed_cnt,
            )

    def action_apply_live_payment_method(self):
        self.ensure_one()
        pm = self.payment_method_id
        if not self.target_config_ids:
            raise UserError(_("Please select at least one POS configuration."))

        self.target_config_ids[:1]._validate_safe_live_payment_methods(pm)
        new_cfgs = self.target_config_ids - pm.config_ids
        for cfg in new_cfgs:
            cfg.with_context(bypass_payment_method_ids_forbidden_change=True).write(
                {"payment_method_ids": [Command.link(pm.id)]}
            )
            cfg._notify_live_payment_methods_added(pm)

        open_updated = new_cfgs.filtered("has_active_session")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Saved"),
                "message": _(
                    "Assigned payment method (%(pm)s) to %(total)s POS "
                    "(%(open)s with open sessions).",
                    pm=pm.display_name,
                    total=len(new_cfgs),
                    open=len(open_updated),
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
