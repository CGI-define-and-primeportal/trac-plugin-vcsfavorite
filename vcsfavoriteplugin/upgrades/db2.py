from trac.db import DatabaseManager
from vcsfavoriteplugin.db_default import schemas



def do_upgrade(env, ver, cursor):
    """Removed owner, publish from the table
    """

    #get the new schema
    vcs_favorites = [t for t in schemas if t.name == 'vcs_favorites'][0]
    db_connector, _ = DatabaseManager(env)._get_connector()

    statements = ['DROP TABLE vcs_favorites']
    statements.extend(db_connector.to_sql(vcs_favorites))
    #Remove the old schema and add the new one
    for stmt in statements:
        cursor.execute(stmt)

