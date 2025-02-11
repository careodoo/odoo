from psycopg2 import sql

from odoo import models


class BaseModel(models.AbstractModel):
    """
    Allow to define a model with 'bigint' ID by setting the '_big_id' attribute to True.
    All the relational fields which relate to this model will be of type 'bigint' too.
    You can also manually set an integer field to 'bigint' by adding 'bigint=True' to it.
    """
    _inherit = 'base'
    _big_id = False

    def _auto_init(self):
        cr = self._cr
        columns_to_convert = []
        for field_name, field in self._fields.items():
            if field_name == 'id' and self._big_id:
                field.column_type = ('bigint', 'bigint')
                # Because id is a special column and only create via first database initialization
                # so it won't convert into bigint serial unless we take action here
                columns_to_convert.append((self._table, 'id'))
            elif field.type == 'many2one' and self.env[field.comodel_name]._big_id:
                field.column_type = ('bigint', 'bigint')
            elif field.type == 'integer' and getattr(field, 'bigint', None):
                field.column_type = ('bigint', 'bigint')
            elif field.type == 'many2many' and field.store:
                if self._big_id:
                    columns_to_convert.append((field.relation, field.column1))
                if self.env[field.comodel_name]._big_id:
                    columns_to_convert.append((field.relation, field.column2))

        super(BaseModel, self)._auto_init()

        for table, column in columns_to_convert:
            cr.execute(
                "SELECT data_type FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
                (table, column),
            )
            res = cr.fetchone()
            if res and res[0] != 'bigint':
                cr.execute(
                    sql.SQL("ALTER TABLE {table} ALTER COLUMN {column} TYPE bigint").format(
                        table=sql.Identifier(table),
                        column=sql.Identifier(column),
                    )
                )
