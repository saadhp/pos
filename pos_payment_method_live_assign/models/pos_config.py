# Copyright 2026 Saad Elbahi
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from markupsafe import Markup, escape

from odoo import Command, _, fields, models
from odoo.exceptions import UserError


def resolve_target_m2m_ids(current_ids, commands):
    result = set(current_ids)
    if not isinstance(commands, list):
        return result
    for cmd in commands:
        if not isinstance(cmd, list | tuple) or not cmd:
            continue
        op = cmd[0]
        if op == Command.LINK and len(cmd) >= 2:
            result.add(cmd[1])
        elif op in (Command.UNLINK, Command.DELETE) and len(cmd) >= 2:
            result.discard(cmd[1])
        elif op == Command.CLEAR:
            result.clear()
        elif op == Command.SET and len(cmd) >= 3:
            result = set(cmd[2] or [])
    return result


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _validate_safe_live_payment_methods(self, added_pms):
        for pm in added_pms:
            if pm.is_cash_count or (pm.journal_id and pm.journal_id.type == "cash"):
                raise UserError(
                    _(
                        "Cash payment method (%s) cannot be added while a session "
                        "is open. Only non-cash payment methods are allowed.",
                        pm.display_name,
                    )
                )
            if not pm.split_transactions and not pm.journal_id:
                raise UserError(
                    _(
                        "Please configure an accounting journal on payment method "
                        "(%s) first.",
                        pm.display_name,
                    )
                )

    def _compute_live_pm_changes(self, vals):
        from_settings = self.env.context.get("from_settings_view", False)
        added_by_cfg = {}
        raw_cmds = vals["payment_method_ids"]
        for cfg in self:
            if not cfg.session_ids.filtered(lambda s: s.state != "closed"):
                continue
            current_ids = set(cfg.payment_method_ids.ids)
            if (
                from_settings
                and isinstance(raw_cmds, list)
                and raw_cmds
                and all(
                    isinstance(c, list | tuple) and c and c[0] == Command.LINK
                    for c in raw_cmds
                )
            ):
                target_ids = {c[1] for c in raw_cmds}
            else:
                target_ids = resolve_target_m2m_ids(current_ids, raw_cmds)

            removed_ids = current_ids - target_ids
            if removed_ids:
                removed_names = ", ".join(
                    self.env["pos.payment.method"]
                    .browse(list(removed_ids))
                    .mapped("display_name")
                )
                raise UserError(
                    _(
                        "Cannot remove existing payment method (%(methods)s) from "
                        "POS (%(pos)s) while a session is open.",
                        methods=removed_names,
                        pos=cfg.display_name,
                    )
                )
            added_ids = target_ids - current_ids
            if added_ids:
                added_pms = self.env["pos.payment.method"].browse(list(added_ids))
                cfg._validate_safe_live_payment_methods(added_pms)
                added_by_cfg[cfg.id] = added_pms
        return added_by_cfg

    def write(self, vals):
        opened_sessions = self.mapped("session_ids").filtered(
            lambda s: s.state != "closed"
        )
        if (
            opened_sessions
            and "payment_method_ids" in vals
            and not self.env.context.get("bypass_payment_method_ids_forbidden_change")
        ):
            added_by_cfg = self._compute_live_pm_changes(vals)
            res = super(
                PosConfig,
                self.with_context(bypass_payment_method_ids_forbidden_change=True),
            ).write(vals)
            for cfg in self:
                added_pms = added_by_cfg.get(cfg.id)
                if added_pms:
                    cfg._notify_live_payment_methods_added(added_pms)
            return res
        return super().write(vals)

    def _notify_live_payment_methods_added(self, added_pms):
        self.ensure_one()
        open_sessions = self.session_ids.filtered(lambda s: s.state != "closed")
        if not open_sessions or not added_pms:
            return

        pm_names = ", ".join(added_pms.mapped("name"))
        user_name = self.env.user.display_name
        now_str = fields.Datetime.to_string(fields.Datetime.now())
        body = Markup(
            _(
                "Payment method added during open session: <b>%(methods)s</b> "
                "by %(user)s (%(timestamp)s UTC)"
            )
        ) % {
            "methods": escape(pm_names),
            "user": escape(user_name),
            "timestamp": escape(now_str),
        }
        for sess in open_sessions:
            sess.message_post(body=body)

        self._notify(
            (
                "LIVE_PAYMENT_METHOD_ADDED",
                {
                    "config_id": self.id,
                    "payment_method_ids": added_pms.ids,
                    "payment_method_names": added_pms.mapped("name"),
                },
            )
        )
