from odoo.addons.stock.tests.common import TestStockCommon


class TestReturnLocation(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.return_location_a = cls.env["stock.location"].create({
            "name": "Return Location A",
            "usage": "internal",
            "location_id": cls.stock_location.location_id.id,
            "company_id": cls.env.company.id,
        })
        cls.return_location_b = cls.env["stock.location"].create({
            "name": "Return Location B",
            "usage": "internal",
            "location_id": cls.stock_location.location_id.id,
            "company_id": cls.env.company.id,
        })

    def _create_done_delivery(self):
        self.env["stock.quant"]._update_available_quantity(self.productA, self.stock_location, 20)
        self.env["stock.quant"]._update_available_quantity(self.productB, self.stock_location, 20)
        picking = self.PickingObj.create({
            "picking_type_id": self.picking_type_out.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
        })
        move_a = self.MoveObj.create({
            "product_id": self.productA.id,
            "product_uom_qty": 2,
            "product_uom": self.uom_unit.id,
            "picking_id": picking.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
        })
        move_b = self.MoveObj.create({
            "product_id": self.productB.id,
            "product_uom_qty": 3,
            "product_uom": self.uom_unit.id,
            "picking_id": picking.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
        })
        picking.action_confirm()
        picking.action_assign()
        move_a.quantity = 2
        move_b.quantity = 3
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def _create_return_wizard(self, picking):
        return self.env["stock.return.picking"].with_context(
            active_id=picking.id,
            active_ids=picking.ids,
            active_model="stock.picking",
        ).create({})

    def test_return_is_split_by_selected_location(self):
        delivery = self._create_done_delivery()
        wizard = self._create_return_wizard(delivery)

        line_a = wizard.product_return_moves.filtered(lambda line: line.product_id == self.productA)
        line_b = wizard.product_return_moves.filtered(lambda line: line.product_id == self.productB)
        line_a.quantity = 1
        line_b.quantity = 2
        line_a.return_location_id = self.return_location_a
        line_b.return_location_id = self.return_location_b

        action = wizard.action_create_returns()
        return_pickings = self.env["stock.picking"].search([("return_id", "=", delivery.id)])

        self.assertEqual(action["view_mode"], "list,form")
        self.assertEqual(len(return_pickings), 2)
        self.assertSetEqual(
            set(return_pickings.mapped("location_dest_id").ids),
            {self.return_location_a.id, self.return_location_b.id},
        )
        picking_a = return_pickings.filtered(lambda picking: picking.location_dest_id == self.return_location_a)
        picking_b = return_pickings.filtered(lambda picking: picking.location_dest_id == self.return_location_b)
        self.assertEqual(picking_a.move_ids.product_id, self.productA)
        self.assertEqual(picking_b.move_ids.product_id, self.productB)
        self.assertEqual(picking_a.move_ids.product_uom_qty, 1)
        self.assertEqual(picking_b.move_ids.product_uom_qty, 2)

    def test_single_selected_location_updates_return_destination(self):
        delivery = self._create_done_delivery()
        wizard = self._create_return_wizard(delivery)

        wizard.product_return_moves.quantity = 1
        wizard.apply_all_return_location_id = self.return_location_a

        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])

        self.assertSetEqual(
            set(wizard.product_return_moves.mapped("return_location_id").ids),
            {self.return_location_a.id},
        )
        self.assertEqual(return_picking.location_dest_id, self.return_location_a)
        self.assertEqual(return_picking.return_id, delivery)
