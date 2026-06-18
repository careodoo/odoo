import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Modify any existing data to ensure compatibility with new function."""
    _logger.info("Running post-init hook for translation compatibility")
    env = api.Environment(env.cr, SUPERUSER_ID, {})
    
    try:
        # Clean up any potentially problematic translations
        env.cr.execute("""
        UPDATE ir_translation 
        SET value = '{}' 
        WHERE value IS NOT NULL 
          AND value NOT LIKE '{%}' 
          AND value != ''
          AND res_id IN (SELECT id FROM security_gate_pass) 
          AND type = 'model'
        """)
        _logger.info("Successfully cleaned up translations")
    except Exception as e:
        _logger.error("Failed to clean up translations: %s", str(e))
