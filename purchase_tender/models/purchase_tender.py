# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BidType(models.Model):
    _name = 'bid.type'
    _description = 'Bid Type'
    _order = 'id desc'

    name = fields.Char()
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)


class TenderFollower(models.Model):
    _name = 'purchase.tender.follower'
    _description = 'Tender Follower'
    _order = 'id desc'

    followers = fields.Many2many('res.users')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)


class PurchaseTender(models.Model):
    _name = 'purchase.tender'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Purchase Tender'
    _order = 'id desc'

    name = fields.Char(required=True)
    tender_no = fields.Char()
    organization = fields.Many2one('res.partner', required=True)
    tender_name = fields.Char()
    issue_date = fields.Date()
    closing_date = fields.Date()
    new_closing_date = fields.Date()
    initial_meeting_date = fields.Date()
    bid_type = fields.Many2one('bid.type', string='Bidding Type')
    current_co = fields.Many2one('res.partner')
    price = fields.Float()
    guarantee = fields.Float()
    period = fields.Integer()
    manpower = fields.Integer()
    winner = fields.Many2one('res.partner', compute='compute_winner', store=True)
    winner_price = fields.Float(compute='compute_winner', store=True)
    winner_rate_price = fields.Float(compute='compute_winner', store=True)
    care_rank = fields.Integer(compute='compute_winner', store=True)
    to_win = fields.Float(compute='compute_to_win', store=True)
    state = fields.Selection(selection=[
        ('new', 'New'),
        ('participated', 'Participated'),
        ('interested', 'Interested'),
        ('excepted', 'Excepted'),
        ('winner', 'Winner'),
        ('purchased', 'Purchased'),
        ('postponed', 'Postponed'),
        ('lost', 'Lost'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], default='new')
    image = fields.Binary(related='organization.image_1920', store=True)

    price_analysis_ids = fields.One2many('purchase.tender.price.analysis', 'tender_id')
    manpower_analysis_ids = fields.One2many('purchase.tender.manpower.analysis', 'tender_id')
    vehicle_analysis_ids = fields.One2many('purchase.tender.vehicle.analysis', 'tender_id')
    material_info_ids = fields.One2many('purchase.tender.material.info', 'tender_id')
    equipment_analysis_ids = fields.One2many('purchase.tender.equipment.analysis', 'tender_id')
    initial_meeting_ids = fields.One2many('purchase.tender.initial.meeting', 'tender_id')
    partner_id = fields.Many2one('res.partner')
    expiry_date = fields.Date()
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)

    @api.onchange('organization')
    def onchange_organization(self):
        for rec in self:
            if rec.organization:
                rec.partner_id = rec.organization.id

    @api.onchange('period')
    def check_period(self):
        if self.period:
            if self.period <= 0:
                self.period = 1

    @api.onchange('manpower')
    def check_manpower(self):
        if self.manpower:
            if self.manpower <= 0:
                self.manpower = 1

    @api.model
    def create(self, vals):
        res = super(PurchaseTender, self).create(vals)
        followers = self.env['purchase.tender.follower'].search([]).mapped('followers')
        if followers:
            for follower in followers:
                res.sudo().activity_schedule(
                    'purchase_tender.mail_act_tender_create',
                    summary='Purchase Tender',
                    note='New tender has been created',
                    user_id=follower.id)
                if res.closing_date or res.new_closing_date or res.initial_meeting_date:
                    close_date_note = 'Tender closing date is {} \n'.format(res.closing_date) if res.closing_date else ''
                    new_close_date_note = 'Tender new closing date is {} \n'.format(res.new_closing_date) if res.new_closing_date else ''
                    initial_meeting_date_note = 'Tender initial meeting date is {}'.format(res.initial_meeting_date) if res.initial_meeting_date else ''
                    note = close_date_note + new_close_date_note + initial_meeting_date_note
                    res.sudo().activity_schedule(
                        'purchase_tender.mail_act_tender_create',
                        summary='Purchase Tender Date Update',
                        note=note,
                        user_id=follower.id)
        return res

    def write(self, values):
        res = super(PurchaseTender, self).write(values)
        followers = self.env['purchase.tender.follower'].search([]).mapped('followers')
        if followers:
            if values.get('state', False):
                if values['state'] in ['postponed', 'cancelled']:
                    for follower in followers:
                        self.sudo().activity_schedule(
                            'purchase_tender.mail_act_tender_create',
                            summary='Purchase Tender',
                            note='Tender status changed to {}'.format(values['state']),
                            user_id=follower.id)
            if values.get('closing_date', False) or values.get('new_closing_date', False) or values.get('initial_meeting_date', False):
                for follower in followers:
                    close_date_note = 'Tender closing date is {} \n'.format(values['closing_date']) if values.get('closing_date') else ''
                    new_close_date_note = 'Tender new closing date is {} \n'.format(
                        values['new_closing_date']) if values.get('new_closing_date') else ''
                    initial_meeting_date_note = 'Tender initial meeting date is {}'.format(
                        values['initial_meeting_date']) if values.get('initial_meeting_date') else ''
                    note = close_date_note + new_close_date_note + initial_meeting_date_note
                    self.sudo().activity_schedule(
                        'purchase_tender.mail_act_tender_create',
                        summary='Purchase Tender Date Update',
                        note=note,
                        user_id=follower.id)
        return res

    @api.depends('price', 'winner_price', 'winner')
    def compute_to_win(self):
        for rec in self:
            care_bid = rec.price_analysis_ids.filtered(lambda p: p.contact.id == self.env.company.sudo().partner_id.id)
            if care_bid and care_bid.price and rec.winner_price and rec.winner.id != self.env.company.sudo().partner_id.id:
                rec.to_win = care_bid.price - rec.winner_price
            else:
                rec.to_win = 0

    @api.depends('price_analysis_ids')
    def compute_winner(self):
        for rec in self:
            rec.winner = False
            rec.winner_price = False
            rec.winner_rate_price = False
            rec.care_rank = False
            if rec.price_analysis_ids:
                winner = min([rec.price for rec in rec.price_analysis_ids])
                winners = rec.price_analysis_ids.filtered(lambda p: p.price == winner)
                rec.winner = winners[0].contact.id if winners else False
                rec.winner_price = winners[0].price if winners else False
                rec.winner_rate_price = winners[0].rate if winners else False
            # get care rank
                care_bid = rec.price_analysis_ids.filtered(lambda p: p.contact.id == self.env.company.sudo().partner_id.id)
                if care_bid:
                    rec.care_rank = care_bid[0].rank


    def name_get(self):
        result = []
        for tender in self:
            name = tender.name + (' - ' + tender.tender_no if tender.tender_no else '') + (' - ' + tender.organization.name if tender.organization else '')
            result.append((tender.id, name))
        return result


class TenderPriceAnalysis(models.Model):
    _name = 'purchase.tender.price.analysis'
    _description = 'Purchase Tender Price Analysis'
    _order = 'id desc'

    name = fields.Char(string="Description")
    sequence = fields.Integer(default=10)
    rank = fields.Integer(compute='compute_rank', store=True)
    contact = fields.Many2one('res.partner')
    price = fields.Float()
    rate = fields.Float(compute='compute_rate', store=True)
    tender_id = fields.Many2one('purchase.tender')
    state = fields.Selection(selection=[
        ('accepted', 'Accepted'),
        ('excepted', 'Excepted'),
    ], string='Status', default='accepted')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)

    @api.depends('tender_id.manpower', 'tender_id.period', 'price')
    def compute_rate(self):
        for rec in self:
            if rec.tender_id.manpower and rec.tender_id.period and rec.price:
                rec.rate = rec.price / rec.tender_id.period / rec.tender_id.manpower
            else:
                rec.rate = 0

    @api.depends('price', 'tender_id.price_analysis_ids', 'state')
    def compute_rank(self):
        for rec in self:
            rec.rank = 0
            if rec.price and rec.tender_id.price_analysis_ids and rec.state != 'excepted':
                prices = rec.tender_id.price_analysis_ids.filtered(lambda p: p.state != 'excepted').mapped('price')
                prices.sort()
                lst = [i for i, x in enumerate(prices) if x == rec.price]
                if len(lst):
                    rec.rank = lst[0] + 1
                    rec.sequence = rec.rank
            else:
                rec.rank = 0
                rec.sequence = 100


class TenderManpowerAnalysis(models.Model):
    _name = 'purchase.tender.manpower.analysis'
    _description = 'Purchase Tender Manpower Analysis'
    _order = 'id desc'

    name = fields.Char(required=True, string="Description")
    sequence = fields.Integer(default=10)
    qty = fields.Float()
    tender_id = fields.Many2one('purchase.tender')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)


class TenderVehicleAnalysis(models.Model):
    _name = 'purchase.tender.vehicle.analysis'
    _description = 'Purchase Tender Vehicle Analysis'
    _order = 'id desc'

    name = fields.Char(required=True, string="Description")
    sequence = fields.Integer(default=10)
    qty = fields.Float()
    tender_id = fields.Many2one('purchase.tender')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)


class TenderMaterialInfo(models.Model):
    _name = 'purchase.tender.material.info'
    _description = 'Purchase Tender Material Info'
    _order = 'id desc'

    name = fields.Char(required=True, string="Description")
    sequence = fields.Integer(default=10)
    action = fields.Char()
    tender_id = fields.Many2one('purchase.tender')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)


class TenderEquipmentAnalysis(models.Model):
    _name = 'purchase.tender.equipment.analysis'
    _description = 'Purchase Tender Equipment Analysis'
    _order = 'id desc'

    name = fields.Char(required=True, string="Description")
    sequence = fields.Integer(default=10)
    qty = fields.Float()
    tender_id = fields.Many2one('purchase.tender')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)


class TenderInitialMeeting(models.Model):
    _name = 'purchase.tender.initial.meeting'
    _description = 'Purchase Tender Initial Meeting'
    _order = 'id desc'

    name = fields.Char(required=True, string="Description")
    sequence = fields.Integer(default=10)
    date = fields.Date()
    file = fields.Binary()
    tender_id = fields.Many2one('purchase.tender')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
