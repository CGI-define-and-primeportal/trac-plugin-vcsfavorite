from trac.core import TracError, Component, implements
from trac.env import IEnvironmentSetupParticipant
from trac.db.api import DatabaseManager, with_transaction
from vcsfavoriteplugin import db_default

class VCSFavoriteDBManager(Component):
    implements(IEnvironmentSetupParticipant)

    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        @self.env.with_transaction()
        def do_db_create(db):
            cursor = db.cursor()
            for table in db_default.schemas:
                self._create_table(cursor, table)
            self._create_or_update_table_version(db_default.name,
                                                 db_default.version
                                                 )

    def _create_or_update_table_version(self,schema_name,version):
        @self.env.with_transaction()
        def do_db_create_or_update(db):
            try:
                cursor = db.cursor()
                cursor.execute('INSERT INTO system (name, value) VALUES (%s, %s)',
                               (db_default.name, db_default.version))
            except Exception:
                cursor = db.cursor()
                cursor.execute('UPDATE system SET value=%s WHERE name=%s',
                               (db_default.version, db_default.name))

    def _create_table(self,cursor,table):
        db_manager, _ = DatabaseManager(self.env)._get_connector()
        for sql in db_manager.to_sql(table):
            self.log.debug('Creating table %s ...' % table.name)
            cursor.execute(sql)

    def _create_non_existing_tabels(self):
        @self.env.with_transaction()
        def check(db):
            cursor = db.cursor()
            for table in db_default.schemas:
                try:
                    sql = 'SELECT * FROM %s' % table.name
                    cursor.execute(sql)
                    cursor.fetchone()
                except Exception:
                    self.log.debug('No table found with name %s' % table.name)
                    self._create_table(cursor, table)
                    return

    def environment_needs_upgrade(self, db):
        cursor = db.cursor()
        cursor.execute('SELECT value FROM system WHERE name=%s',
                       (db_default.name,))
        value = cursor.fetchone()

        if not value:
            self.found_db_version = 0
        else:
            self.found_db_version = int(value[0])

        if self.found_db_version < db_default.version:
            return True
        elif self.found_db_version > db_default.version:
            raise TracError('Database newer than %s version', db_default.name)
        else:
            return False

    def upgrade_environment(self, db):

        #Create all non existing tables in the schema.
        self._create_non_existing_tabels()

        cursor = db.cursor()

        #Run all update from old version to current version
        for i in range(self.found_db_version+1, db_default.version+1):
            name = 'db%i' % i
            try:
                upgrades = __import__('upgrades', globals(), locals(), [name])
                script = getattr(upgrades, name)
            except AttributeError:
                raise TracError('No upgrade module for %s version %i',
                                db_default.name, i)

            script.do_upgrade(self.env, i, cursor)
            cursor.execute('UPDATE system SET value=%s WHERE name=%s',
                           (db_default.version, db_default.name))
        db.commit()
        self._create_or_update_table_version(db_default.name,
                                     db_default.version
                                     )
        self.log.debug('Upgraded %s database version from %d to %d',
                      db_default.name, i-1, i)



class VCSFavorite(object):

    def __init__(self, env, db_row=None, path='', _id=None, description=u''):
        self.env = env

        if db_row:
            self._id, self.path, self.description, = db_row
        else:
            self._id = _id
            self.path = path
            self.description = description

    def _validate_options(self):
        if not self.path:
            raise TracError("Path is not set.")

    def insert(self):
        self._validate_options()
        @self.env.with_transaction()
        def _do_insert(db):
            cursor = db.cursor()
            try:
                cursor.execute('INSERT INTO vcs_favorites'
                               + ' (path, description)'
                               + ' VALUES (%s, %s)',
                               (self.path, self.description))
            except Exception, e:
                if isinstance(e, "IntegrityError"):
                    raise TracError('Path "%s" already exists' % self.path)
                else:
                    raise e
            self._id = db.get_last_id(cursor, 'vcs_favorites')

    def update(self):
        self._validate_options()
        rowcount = 0
        @with_transaction(self.env)
        def _do_update(db):
            cursor = db.cursor()
            cursor.execute('UPDATE vcs_favorites'
                           + ' SET path=%s, description=%s'
                           + ' WHERE id = %s',
                            (self.path, self.description, self._id))
            rowcount = cursor.rowcount

        return rowcount

    @classmethod
    def select_one(cls, _id, env):
        """ Fetches a VCSFavorite from db """
        try:
            int_id = int(_id)
        except ValueError:
            env.log.error("%s is not an integer. Potential Sql injection atempt" % _id)
        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, path, description FROM vcs_favorites'
                           + ' WHERE id = %s', (int_id,))
        row = cursor.fetchone()
        if row:
            return VCSFavorite(env, db_row=row)

        return None

    @classmethod
    def select_all(cls, env):
        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, path, description FROM vcs_favorites')
        return [VCSFavorite(env, db_row=row) for row in cursor]

    @classmethod
    def select_all_path_begins_with(cls, env, starts_with):
        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute(('SELECT id, path, description'
                        + ' FROM vcs_favorites'
                        + ' WHERE ( path ' + db.like()
                        + ' OR path ' + db.like()
                        + ' OR path ' + db.like()
                        + ' )')
                       , (db.like_escape(starts_with) + '%',
                          db.like_escape(starts_with + '/') + '%',
                          db.like_escape(starts_with[:-1] if starts_with.endswith('/') else starts_with) + '%',
                          )
                       )
        return [VCSFavorite(env, db_row=row) for row in cursor]

    @classmethod
    def remove_one_by_path(cls, path, env):
        rowcount = 0
        #paths is only stored with out trailing /
        path = path[:-1] if path.endswith('/') else path
        @with_transaction(env)
        def _do_remove_one(db):
            cursor = db.cursor()
            cursor.execute('DELETE FROM vcs_favorites WHERE path = %s', (path,))
            rowcount = cursor.rowcount
        return rowcount

    @classmethod
    def remove_one_by_id(cls, _id, env):
        try:
            int_id = int(_id)
        except ValueError:
            env.log.error("%s is not an integer. Potential Sql injection attempt" % _id)
            raise TracError("%s is not an integer. Potential Sql injection atempt" % _id)
        rowcount = 0
        @with_transaction(env)
        def _do_remove_one(db):
            cursor = db.cursor()
            cursor.execute('DELETE FROM vcs_favorites WHERE id = %s', (_id,))
            rowcount = cursor.rowcount
        return rowcount

    @classmethod
    def remove_list_by_id(cls, favorites, env):
        """
        Removes a list of id from favorites.
        """
        nr_rows = 0
        for _id in favorites:
            nr_rows += cls.remove_one_by_id(_id, env)
        return nr_rows
