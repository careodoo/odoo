def migrate(cr, version):
    """
    Apply fixes for jsonb_path_query_first issues in Odoo 18
    
    In Odoo 18, there are changes to how translation fields and JSON data are handled.
    This migration script patches the database to ensure compatibility.
    """
    # Fix any corrupted translation fields in the security.gate.pass model
    cr.execute("""
    UPDATE ir_translation 
    SET value = '{}' 
    WHERE value IS NOT NULL 
      AND value NOT LIKE '{%}' 
      AND res_id IN (SELECT id FROM security_gate_pass) 
      AND type = 'model'
    """)
    
    # Use our compatibility function to fix any SQL views that might be using the function
    cr.execute("""
    ALTER FUNCTION jsonb_path_query_first(character varying, unknown) 
    RENAME TO jsonb_path_query_first_original;
    """)
    
    cr.execute("""
    CREATE OR REPLACE FUNCTION jsonb_path_query_first(text_val character varying, path_val unknown)
    RETURNS jsonb AS $$
    BEGIN
        -- Attempt to cast the values to proper types
        RETURN jsonb_path_query_first(
            CASE 
                WHEN text_val IS NULL THEN NULL::jsonb
                WHEN text_val = '' THEN '{}'::jsonb 
                WHEN text_val ~ '^\\{.*\\}$' THEN text_val::jsonb
                ELSE ('{"value":"' || text_val || '"}')::jsonb
            END, 
            CASE 
                WHEN path_val IS NULL THEN NULL::jsonpath
                ELSE path_val::text::jsonpath
            END);
    EXCEPTION WHEN OTHERS THEN
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)
