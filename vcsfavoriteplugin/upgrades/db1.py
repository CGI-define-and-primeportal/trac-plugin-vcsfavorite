from trac.db import DatabaseManager

from tracremoteticket.db_default import schema

def do_upgrade(env, ver, cursor):
    """Inital schema nothing to do
    """
    print 'Initial upgrade for VCS Favorites'
