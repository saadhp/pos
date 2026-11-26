# Copyright 2026 Saad Elbahi
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosLivePaymentMethod(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.bank_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.company.id), ("type", "=", "bank")],
            limit=1,
        )
        cls.cash_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.company.id), ("type", "=", "cash")],
            limit=1,
        )
        cls.base_pm = cls.env["pos.payment.method"].create(
            {
                "name": "Base Bank PM",
                "journal_id": cls.bank_journal.id,
            }
        )
        cls.extra_bank_pm = cls.env["pos.payment.method"].create(
            {
                "name": "Live Card PM",
                "journal_id": cls.bank_journal.id,
            }
        )
        cls.extra_cash_pm = cls.env["pos.payment.method"].create(
            {
                "name": "Extra Cash PM",
                "journal_id": cls.cash_journal.id,
            }
        )
        cls.pos_config = cls.env["pos.config"].create(
            {
                "name": "Live Assign Test POS",
                "payment_method_ids": [Command.set([cls.base_pm.id])],
            }
        )
        cls.session = cls.env["pos.session"].create(
            {
                "config_id": cls.pos_config.id,
                "user_id": cls.env.user.id,
            }
        )

    def test_assign_non_cash_during_open_session(self):
        self.assertNotEqual(self.session.state, "closed")
        msg_before = len(self.session.message_ids)

        wizard = (
            self.env["pos.live.payment.wizard"]
            .with_context(default_payment_method_id=self.extra_bank_pm.id)
            .create({"target_config_ids": [Command.set([self.pos_config.id])]})
        )
        wizard.action_apply_live_payment_method()

        self.assertIn(self.extra_bank_pm, self.pos_config.payment_method_ids)
        self.assertGreater(len(self.session.message_ids), msg_before)

    def test_block_cash_addition_and_removal_during_open_session(self):
        with self.assertRaises(UserError):
            self.pos_config.write(
                {"payment_method_ids": [Command.link(self.extra_cash_pm.id)]}
            )

        with self.assertRaises(UserError):
            self.pos_config.write(
                {"payment_method_ids": [Command.unlink(self.base_pm.id)]}
            )

        with self.assertRaises(UserError):
            self.extra_cash_pm.action_open_live_assign_wizard()
