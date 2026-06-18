def migrate(cr, version):
    """Add compatibility function for jsonb_path_query_first that can handle character varying inputs"""
    cr.execute("""
    CREATE OR REPLACE FUNCTION public.jsonb_path_query_first_compat(text_val character varying, path_val text)
    RETURNS jsonb AS $$
    BEGIN
        -- Convert the character varying to jsonb before calling the real function
        RETURN jsonb_path_query_first(CAST(text_val AS jsonb), path_val::jsonpath);
    EXCEPTION WHEN OTHERS THEN
        -- Return null in case of errors
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)
