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
            cursor.execute('INSERT INTO system (name, value) VALUES (%s, %s)',
                           (db_default.name, db_default.version))

    def environment_needs_upgrade(self, db):
        current_db_version = self.check_db_version(db)
        if current_db_version > db_default.version:
            raise TracError('Database newer than %s version'
                            % db_default.name)
        return current_db_version < db_default.version

    def upgrade_environment(self, db):
        current_db_version = self.check_db_version(db)
        # If there is no row in system for VCS favorites then the environment
        # was created without this plugin, so we can just create the latest
        # schema
        if current_db_version < 0:
            self.environment_created()
            return
        cursor = db.cursor()
        #Run all update from old version to current version
        for i in xrange(current_db_version + 1, db_default.version + 1):
            name = 'db%i' % i
            try:
                upgrades = __import__('upgrades', globals(), locals(), [name])
                script = getattr(upgrades, name)
            except AttributeError:
                raise TracError("No upgrade module for %s version %s"
                                % (db_default.name, i))
            script.do_upgrade(self.env, i, cursor)
            cursor.execute('UPDATE system SET value=%s WHERE name=%s',
                           (i, db_default.name))
            self.log.debug('Upgraded %s database version from %d to %d',
                           db_default.name, i - 1, i)
            db.commit()

    def check_db_version(self, db):
        """Return the database version recorded in the database, or -1 if no
        version is recorded.
        """
        cursor = db.cursor()
        cursor.execute('SELECT value FROM system WHERE name=%s',
                       (db_default.name,))
        value = cursor.fetchone()
        value = int(value[0]) if value else -1
        return value

    def _create_table(self, cursor, table):
        db_manager, _ = DatabaseManager(self.env)._get_connector()
        for sql in db_manager.to_sql(table):
            cursor.execute(sql)


class VCSFavorite(object):

    def __init__(self, env, db_row=None, path='', _id=None, description=u''):
        self.env = env

        if db_row:
            self._id, self.path, self.description, = db_row
        else:
            self._id = _id
            #paths is only stored with out trailing /
            self.path = path[:-1] if path.endswith('/') else path
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
                if  e.__class__.__name__ == "IntegrityError":
                    raise TracError('Path "%s" already exists', (self.path,))
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
                           (self.path, self.description, self._id)
                           )
            rowcount = cursor.rowcount

        return rowcount

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
                        + ' )'
                        ), (db.like_escape(starts_with) + '%',
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
