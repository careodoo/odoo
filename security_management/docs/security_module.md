# Security Management Module - Technical Documentation

## 1. Overview

The Security Management module is a comprehensive platform designed to streamline security operations, enhance accountability, and improve client transparency. It provides a structured approach to security service management including guard tracking, key management, premises monitoring, patrol verification, and incident reporting.

## 2. Architecture and Core Components

The module follows a modular architecture with several interconnected components:

```bash
security_management/
├── controllers/          # HTTP controllers for web interfaces
├── data/                 # Default data and sequences
├── demo/                 # Demo/test data
├── docs/                 # Documentation
├── models/               # Data models (business logic)
├── reports/              # Report templates
├── security/             # Access rights and rules
├── static/               # Static assets (JS, CSS)
├── tests/                # Automated tests
├── views/                # UI views
└── wizards/              # Wizard interfaces
```

### 2.1 Module Definition

The module is defined in `__manifest__.py`, which specifies its dependencies, data files, and assets. Key dependencies include:

- base
- hr (Human Resources)
- mail (Communication)
- portal (Client portal access)
- web (UI framework)
- resource (Resource scheduling)
- contacts (Contact management)
- account (Accounting integration)
- report_xlsx (Excel reporting)
- hr_attendance (Attendance tracking)
- hr_contract (Contract management)

### 2.2 Data Flow

1. **User Authentication & Authorization**: Users are assigned to security groups that determine their access rights
2. **Client Management**: Clients are created with contracts and premises
3. **Team & Guard Management**: Security teams and guards are assigned to clients and premises
4. **Operations**: Daily operations including patrol management, key handling, incident reporting
5. **Reporting**: Generation of reports for analysis and client transparency

## 3. Security Model

The security model defines four main access levels:

```xml
<!-- Security Groups -->
<record id="group_security_user" model="res.groups">
    <field name="name">User</field>
    <field name="category_id" ref="module_security_manager_category"/>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
</record>

<record id="group_security_guard" model="res.groups">
    <field name="name">Guard</field>
    <field name="category_id" ref="module_security_manager_category"/>
    <field name="implied_ids" eval="[(4, ref('group_security_user'))]"/>
</record>

<record id="group_security_manager" model="res.groups">
    <field name="name">Manager</field>
    <field name="category_id" ref="module_security_manager_category"/>
    <field name="implied_ids" eval="[(4, ref('group_security_guard'))]"/>
</record>

<record id="group_security_admin" model="res.groups">
    <field name="name">Administrator</field>
    <field name="category_id" ref="module_security_manager_category"/>
    <field name="implied_ids" eval="[(4, ref('group_security_manager'))]"/>
</record>
```

These groups follow a hierarchical structure:

- **User**: Basic access to view information
- **Guard**: Field operations including checkpoints and incident reporting
- **Manager**: Manage teams and operations
- **Administrator**: Full system access including configuration

## 4. Core Models

### 4.1 Client Management (`security.client`)

The client model manages customer information and contract details:

```python
class SecurityClient(models.Model):
    _name = 'security.client'
    _description = 'Security Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char('Client Name', required=True, tracking=True)
    contact_id = fields.Many2one('res.partner', string='Primary Contact', required=True)
    contract_start_date = fields.Date('Contract Start Date', required=True)
    contract_end_date = fields.Date('Contract End Date', required=True)
    contract_state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
    ], compute='_compute_contract_state')
```

### 4.2 Security Team (`security.team`)

Teams are groups of security personnel assigned to clients:

```python
class SecurityTeam(models.Model):
    _name = 'security.team'
    _description = 'Security Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Team Name', required=True)
    code = fields.Char(string='Team Code', required=True)
    client_id = fields.Many2one('security.client', string='Client', required=True)
    leader_id = fields.Many2one('security.employee', string='Team Leader')
    member_ids = fields.Many2many('security.employee', string='Team Members')
    team_type = fields.Selection([
        ('day', 'Day'),
        ('night', 'Night')
    ], string='Team Type', required=True, default='day')
```

### 4.3 Key Management (`security.key`)

Tracks physical keys for premises access:

```python
class SecurityKey(models.Model):
    _name = 'security.key'
    _description = 'Security Key'
    
    name = fields.Char(string='Key Name', required=True)
    door_number = fields.Char(string='Door Number', required=True)
    key_number = fields.Char(string='Key Number', required=True)
    key_type = fields.Selection([
        ('master', 'Master Key'),
        ('room', 'Room Key'),
        ('cabinet', 'Cabinet Key'),
        ('padlock', 'Padlock Key'),
        ('other', 'Other')
    ], string='Key Type', default='room')
    state = fields.Selection([
        ('available', 'Available'),
        ('checked_out', 'Checked Out'),
        ('maintenance', 'Maintenance'),
        ('lost', 'Lost')
    ], string='Status', default='available')
    current_holder_id = fields.Many2one('hr.employee', string='Current Holder')
```

### 4.4 Premises Management (`security.premise`)

Represents physical locations that require security services:

```python
class SecurityPremise(models.Model):
    _name = 'security.premise'
    _description = 'Security Premise'
    
    name = fields.Char(string='Name', required=True)
    address = fields.Text(string='Address', required=True)
    client_id = fields.Many2one('security.client', string='Client')
    floor_ids = fields.One2many('security.floor', 'premise_id', string='Floors')
    unit_ids = fields.One2many('security.unit', 'premise_id', string='Units')
```

## 5. Feature Details

### 5.1 Dashboard and Analytics

The system provides real-time dashboards for monitoring security operations:

```javascript
// security_dashboard.js
get_dashboard_data: function() {
    return this._rpc({
        model: 'security.team',
        method: 'get_dashboard_data',
        args: [],
    }).then(function (result) {
        return result;
    });
}
```

The backend model supports this functionality:

```python
@api.model
def get_dashboard_data(self):
    """Get data for the security dashboard"""
    # Get client count
    client_count = self.env['security.client'].search_count([])
    
    # Get post site count
    post_site_count = self.env['security.post.site'].search_count([])
    
    # Get security guard count
    security_group = self.env.ref('security_management.group_security_guard', False)
    guard_count = len(security_group.users) if security_group else 0
    
    # Additional metrics and guard tracking data
    # ...
    
    return {
        'client_count': client_count,
        'post_site_count': post_site_count,
        'guard_count': guard_count,
        # Other metrics
    }
```

### 5.2 Patrol Management

Patrol management tracks guard movements and checkpoint verification:

```python
class SecurityPatrolLog(models.Model):
    _name = 'security.patrol.log'
    _description = 'Patrol Log'
    
    patrol_id = fields.Many2one('security.patrol', required=True)
    guard_id = fields.Many2one('security.employee', required=True)
    checkpoint_id = fields.Many2one('security.patrol.checkpoint', required=True)
    check_time = fields.Datetime('Check Time', default=fields.Datetime.now)
    status = fields.Selection([
        ('on_time', 'On Time'),
        ('late', 'Late'),
        ('missed', 'Missed')
    ], compute='_compute_status')
    location_latitude = fields.Float('Latitude')
    location_longitude = fields.Float('Longitude')
```

### 5.3 Incident Reporting

The system allows for detailed reporting of security incidents:

```python
class SecurityIncident(models.Model):
    _name = 'security.incident'
    _description = 'Security Incident'
    
    name = fields.Char('Title', required=True)
    date = fields.Datetime('Date & Time', default=fields.Datetime.now)
    reporter_id = fields.Many2one('security.employee', 'Reported By')
    premise_id = fields.Many2one('security.premise', 'Location')
    description = fields.Text('Description')
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], default='medium')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('reported', 'Reported'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], default='draft')
```

## 6. Advanced Configuration

### 6.1 System Configuration Parameters

The module uses system parameters for configuration, accessible via:

```python
def get_param(self, param_name, default=None):
    param = self.env['ir.config_parameter'].sudo().get_param(
        f'security_management.{param_name}', default
    )
    return param
```

### 6.2 Key Configuration Parameters

Common configuration parameters include:

| Parameter | Description | Default |
| --- | --- | --- |
| patrol_interval | Time between patrol checks (minutes) | 30 |
| key_checkout_duration | Default key checkout duration (hours) | 8 |
| incident_auto_notify | Auto-notify managers for high severity incidents | True |
| guard_tracking_interval | GPS tracking interval for guards (minutes) | 5 |

### 6.3 Module Extension Points

The module provides several extension hooks for customizing functionality:

1. **Custom Reports**: Extend base reports by inheriting report templates
2. **Additional Security Roles**: Create new security roles and permissions
3. **Custom Dashboard Metrics**: Add custom metrics to the dashboard
4. **Workflow Customization**: Extend the base workflows with additional states and transitions

## 7. Integration with External Systems

### 7.1 GPS Tracking Integration

The module supports integration with GPS tracking systems:

```python
def update_guard_locations(self, tracking_data):
    """Update guard locations from GPS tracking system"""
    for guard_data in tracking_data:
        guard = self.env['security.guard'].search([
            ('tracking_id', '=', guard_data['tracking_id'])
        ], limit=1)
        
        if guard:
            guard.write({
                'latitude': guard_data['latitude'],
                'longitude': guard_data['longitude'],
                'last_update': fields.Datetime.now(),
                'battery_level': guard_data.get('battery_level', 0),
                'speed': guard_data.get('speed', 0)
            })
            
            # Create tracking record
            self.env['security.tracking.log'].create({
                'guard_id': guard.id,
                'latitude': guard_data['latitude'],
                'longitude': guard_data['longitude'],
                'timestamp': fields.Datetime.now(),
                'battery_level': guard_data.get('battery_level', 0)
            })
```

### 7.2 Biometric System Integration

For access control and time tracking:

```python
def process_biometric_event(self, event_data):
    """Process events from biometric systems"""
    employee = self.env['security.employee'].search([
        ('biometric_id', '=', event_data['employee_id'])
    ], limit=1)
    
    if not employee:
        return False, "Employee not found"
        
    if event_data['event_type'] == 'check_in':
        # Create attendance record
        self.env['security.attendance'].create({
            'employee_id': employee.id,
            'check_in': fields.Datetime.now(),
            'location_id': event_data.get('location_id', False)
        })
    elif event_data['event_type'] == 'check_out':
        # Find open attendance
        attendance = self.env['security.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)
        
        if attendance:
            attendance.write({
                'check_out': fields.Datetime.now(),
                'worked_hours': (fields.Datetime.now() - attendance.check_in).total_seconds() / 3600
            })
            
    return True, "Event processed"
```

## 8. Best Practices and Recommendations

### 8.1 Performance Optimization

- Use indexing for frequently queried fields:

  ```python
  name = fields.Char(index=True)
  ```
  
- Use prefetching for related records:

  ```python
  def _read_group_process_groupby(self, groupby, query):
      if groupby == 'client_id':
          return query.prefetch(['client_id', 'client_id.name'])
      return super()._read_group_process_groupby(groupby, query)
  ```

### 8.2 Security Recommendations

- Implement proper field-level access control for sensitive data:

  ```xml
  <field name="private_notes" groups="security_management.group_security_manager"/>
  ```
  
- Use proper record rules for multi-company environments:

  ```xml
  <record id="security_incident_comp_rule" model="ir.rule">
      <field name="name">Security Incident: Multi-company</field>
      <field name="model_id" ref="model_security_incident"/>
      <field name="global" eval="True"/>
      <field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]</field>
  </record>
  ```

### 8.3 Audit Trail

The module uses `mail.thread` mixin to track changes to important records:

```python
class SecurityIncident(models.Model):
    _name = 'security.incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], default='medium', tracking=True)
```

## 9. Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
| --- | --- |
| Missing patrol records | Check GPS connectivity and patrol schedule configuration |
| Key management issues | Verify key checkout process and user permissions |
| Report generation failures | Check report templates and ensure all required fields are available |

### Logging and Debugging

Enable detailed logging for troubleshooting:

```python
import logging
_logger = logging.getLogger(__name__)

def process_biometric_event(self, event_data):
    try:
        _logger.info("Processing biometric event: %s", event_data.get('employee_id'))
        employee = self.env['security.employee'].search([
            ('biometric_id', '=', event_data['employee_id'])
        ], limit=1)
        
        if not employee:
            return False, "Employee not found"
            
        if event_data['event_type'] == 'check_in':
            # Create attendance record
            self.env['security.attendance'].create({
                'employee_id': employee.id,
                'check_in': fields.Datetime.now(),
                'location_id': event_data.get('location_id', False)
            })
        elif event_data['event_type'] == 'check_out':
            # Find open attendance
            attendance = self.env['security.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)
            
            if attendance:
                attendance.write({
                    'check_out': fields.Datetime.now(),
                    'worked_hours': (fields.Datetime.now() - attendance.check_in).total_seconds() / 3600
                })
                
        return True, "Event processed"
    except Exception as e:
        _logger.error("Biometric event error: %s", str(e))
        raise
