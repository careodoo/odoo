from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.osv.expression import OR
from collections import OrderedDict


class SecurityPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        
        partner = request.env.user.partner_id
        SecurityClient = request.env['security.client']
        SecurityTask = request.env['security.task']
        SecurityInspection = request.env['security.inspection']
        SecurityGatePass = request.env['security.gate.pass']
        
        if 'client_count' in counters:
            values['client_count'] = SecurityClient.search_count([
                ('contact_id', '=', partner.id)
            ]) if SecurityClient.check_access_rights('read', raise_exception=False) else 0
            
        if 'task_count' in counters:
            values['task_count'] = SecurityTask.search_count([
                '|',
                ('client_id.contact_id', '=', partner.id),
                ('contact_id', '=', partner.id)
            ]) if SecurityTask.check_access_rights('read', raise_exception=False) else 0
            
        if 'inspection_count' in counters:
            values['inspection_count'] = SecurityInspection.search_count([
                ('client_id.contact_id', '=', partner.id)
            ]) if SecurityInspection.check_access_rights('read', raise_exception=False) else 0
            
        if 'gate_pass_count' in counters:
            values['gate_pass_count'] = SecurityGatePass.search_count([
                '|',
                ('client_id.contact_id', '=', partner.id),
                ('visitor_id', '=', partner.id)
            ]) if SecurityGatePass.check_access_rights('read', raise_exception=False) else 0
            
        return values
    
    # Tasks Portal
    @http.route(['/my/security/tasks', '/my/security/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_security_tasks(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SecurityTask = request.env['security.task']
        
        domain = [
            '|',
            ('client_id.contact_id', '=', partner.id),
            ('contact_id', '=', partner.id)
        ]
        
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Title'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'due_date': {'label': _('Due Date'), 'order': 'due_date'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'open': {'label': _('Open'), 'domain': [('stage_id.is_closed', '=', False)]},
            'closed': {'label': _('Closed'), 'domain': [('stage_id.is_closed', '=', True)]},
        }
        
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search in Task Description')},
            'name': {'input': 'name', 'label': _('Search in Task Title')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        
        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']
        
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        # search
        if search and search_in:
            search_domain = []
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, [('description', 'ilike', search)]])
            domain += search_domain
        
        # count for pager
        task_count = SecurityTask.search_count(domain)
        
        # pager
        pager = portal_pager(
            url="/my/security/tasks",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            total=task_count,
            page=page,
            step=self._items_per_page
        )
        
        # content according to pager and archive selected
        tasks = SecurityTask.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'date': date_begin,
            'tasks': tasks,
            'page_name': 'security_task',
            'pager': pager,
            'default_url': '/my/security/tasks',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
        })
        return request.render("security_manager.portal_my_security_tasks", values)
    
    @http.route(['/my/security/task/<int:task_id>'], type='http', auth="user", website=True)
    def portal_my_security_task(self, task_id=None, **kw):
        try:
            task_sudo = self._document_check_access('security.task', task_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._security_task_get_page_view_values(task_sudo, **kw)
        return request.render("security_manager.portal_my_security_task", values)
    
    def _security_task_get_page_view_values(self, task, **kwargs):
        values = {
            'page_name': 'security_task',
            'task': task,
        }
        return self._get_page_view_values(task, False, values, 'my_security_tasks_history', False, **kwargs)
    
    # Gate Passes Portal
    @http.route(['/my/security/gate_passes', '/my/security/gate_passes/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_security_gate_passes(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SecurityGatePass = request.env['security.gate.pass']
        
        domain = [
            '|',
            ('client_id.contact_id', '=', partner.id),
            ('visitor_id', '=', partner.id)
        ]
        
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'validity': {'label': _('Validity'), 'order': 'valid_until'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'valid': {'label': _('Valid'), 'domain': [('state', '=', 'valid')]},
            'expired': {'label': _('Expired'), 'domain': [('state', '=', 'expired')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
        }
        
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search in Description')},
            'name': {'input': 'name', 'label': _('Search in Name')},
            'visitor': {'input': 'visitor', 'label': _('Search in Visitor')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        
        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']
        
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        # search
        if search and search_in:
            search_domain = []
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, [('purpose', 'ilike', search)]])
            if search_in in ('visitor', 'all'):
                search_domain = OR([search_domain, [('visitor_id.name', 'ilike', search)]])
            domain += search_domain
        
        # count for pager
        gate_pass_count = SecurityGatePass.search_count(domain)
        
        # pager
        pager = portal_pager(
            url="/my/security/gate_passes",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            total=gate_pass_count,
            page=page,
            step=self._items_per_page
        )
        
        # content according to pager and archive selected
        gate_passes = SecurityGatePass.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'date': date_begin,
            'gate_passes': gate_passes,
            'page_name': 'security_gate_pass',
            'pager': pager,
            'default_url': '/my/security/gate_passes',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
        })
        return request.render("security_manager.portal_my_security_gate_passes", values)
    
    @http.route(['/my/security/gate_pass/<int:gate_pass_id>'], type='http', auth="user", website=True)
    def portal_my_security_gate_pass(self, gate_pass_id=None, **kw):
        try:
            gate_pass_sudo = self._document_check_access('security.gate.pass', gate_pass_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._security_gate_pass_get_page_view_values(gate_pass_sudo, **kw)
        return request.render("security_manager.portal_my_security_gate_pass", values)
    
    def _security_gate_pass_get_page_view_values(self, gate_pass, **kwargs):
        values = {
            'page_name': 'security_gate_pass',
            'gate_pass': gate_pass,
        }
        return self._get_page_view_values(gate_pass, False, values, 'my_security_gate_passes_history', False, **kwargs)
    
    # QR Code Scanner
    @http.route(['/security/scan_qr'], type='http', auth="user", website=True)
    def security_scan_qr(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'security_scan_qr',
        })
        return request.render("security_manager.portal_security_scan_qr", values)
    
    @http.route(['/security/process_qr'], type='json', auth="user", website=True)
    def security_process_qr(self, qr_code, **kw):
        # Check for patrol point
        patrol_point = request.env['security.patrol.point'].sudo().search([('qr_code', '=', qr_code)], limit=1)
        if patrol_point:
            return {
                'type': 'patrol_point',
                'id': patrol_point.id,
                'name': patrol_point.name,
                'location': patrol_point.location,
            }
        
        # Check for key
        key = request.env['security.key'].sudo().search([('qr_code', '=', qr_code)], limit=1)
        if key:
            return {
                'type': 'key',
                'id': key.id,
                'name': key.name,
                'state': key.state,
                'key_hub': key.key_hub_id.name,
            }
        
        # Check for premise
        premise = request.env['security.premise'].sudo().search([('qr_code', '=', qr_code)], limit=1)
        if premise:
            return {
                'type': 'premise',
                'id': premise.id,
                'name': premise.name,
                'address': premise.address,
                'client': premise.client_id.name,
            }
        
        # Check for gate pass
        gate_pass = request.env['security.gate.pass'].sudo().search([('qr_code', '=', qr_code)], limit=1)
        if gate_pass:
            return {
                'type': 'gate_pass',
                'id': gate_pass.id,
                'name': gate_pass.name,
                'visitor': gate_pass.visitor_id.name,
                'valid_until': gate_pass.valid_until,
                'state': gate_pass.state,
            }
        
        return {'error': _('QR Code not recognized')}
