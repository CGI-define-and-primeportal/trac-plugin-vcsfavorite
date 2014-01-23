from trac.core import TracError, Component, implements
from trac.env import IEnvironmentSetupParticipant
from trac.db.schema import Table, Column, Index
from trac.db.api import DatabaseManager, with_transaction
from trac.web.chrome import add_warning

class VCSFavoriteDBManager(Component):
    implements(IEnvironmentSetupParticipant)

    _schema_name = 'vcs_favorites'
    _schemas = [Table(_schema_name, key='id')[Column('id', auto_increment=True),
                                         Column('path', 'text'),
                                         Column('owner', 'text'),
                                         Column('description', 'text'),
                                         Column('published', 'int'),
                                         Index(['path'], unique=True)],]

    #IEnvironmentSetupParticipant
    def environment_created(self):
        """Called when a new Trac environment is created."""
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        """Called when Trac checks whether the environment needs to be upgraded.

        Should return `True` if this participant needs an upgrade to be
        performed, `False` otherwise.
        """
        release_tables = [VCSFavoriteDBManager._schema_name,]
        self.env.log.info("Checking if table %s have to be upgraded" % str(release_tables))

        try:
            @self.env.with_transaction()
            def check(db):
                cursor = db.cursor()
                for table_name in release_tables:
                    sql = 'SELECT * FROM %s' % table_name
                    cursor.execute(sql)
                    cursor.fetchone()
        except Exception:
            self.log.debug('Upgrade of schema needed for VCS Favorites '
                           'plugin', exc_info=True)
            return True

        return False

    def upgrade_environment(self, db):
        """Actually perform an environment upgrade.

        Implementations of this method don't need to commit any database
        transactions. This is done implicitly for each participant
        if the upgrade succeeds without an error being raised.

        However, if the `upgrade_environment` consists of small, restartable,
        steps of upgrade, it can decide to commit on its own after each
        successful step.
        """
        self.log.debug('Upgrading schema for ReleaseManagement plugin')
        connector = DatabaseManager(self.env).get_connector()[0]
        cursor = db.cursor()

        for table in self._schemas:
            for stmt in connector.to_sql(table):
                self.log.debug(stmt)
                try:
                    cursor.execute(stmt)
                except Exception, ex:
                    self.log.error('%s', ex)


class VCSFavorite(object):

    def __init__(self, env, db_row=None, path='', owner='',
                 _id=None, description=u'', published=True):

        self.env = env

        if db_row:
            self._id, self.path, self.owner, \
            self.description, self.published = db_row
        else:
            self._id = _id
            self.path = path
            self.description = description
            self.owner = owner
            self.published = published

    def _validate_options(self):
        if not self.path:
            raise TracError("Path is not set.")

    def insert(self):
        self._validate_options()
        #paths is only stored with out trailing /
        @self.env.with_transaction()
        def _do_insert(db):
            cursor = db.cursor()
            try:
                cursor.execute('INSERT INTO ' + VCSFavoriteDBManager._schema_name
                               + ' (path, owner, description, published)'
                               + ' VALUES (%s, %s, %s, %s)',
                               (self.path,self.owner,self.description,self.published))
            except Exception, e:
                if e.__class__.__name__ == "IntegrityError":
                    raise TracError('Path "%s" already exists' % self.path)
                else:
                    raise e
            self._id = db.get_last_id(cursor, VCSFavoriteDBManager._schema_name )

    def update(self):
        self._validate_options()
        rowcount = 0
        @with_transaction(self.env)
        def _do_update(db):
            cursor = db.cursor()
            cursor.execute('UPDATE ' + VCSFavoriteDBManager._schema_name
                           + ' SET path=%s, owner=%s, description=%s, published=%s'
                           + ' WHERE id = %s',
                            (self.path, self.owner, self.description, self.published,
                            self._id))
            rowcount = cursor.rowcount

        return rowcount

    @classmethod
    def select_one(cls, _id, env, owner=None):
        """ Fetches a VCSFavorite from db """
        try:
            int_id = int(_id)
        except ValueError:
            env.log.error("%s is not an integer. Potential Sql injection atempt" % _id)
        db = env.get_read_db()
        cursor = db.cursor()
        if owner:
            cursor.execute('SELECT id, path, owner, description, published FROM '
                           + VCSFavoriteDBManager._schema_name + ' WHERE id = %s AND owner=%s OR published=1', (int_id,owner))
        else:
            cursor.execute('SELECT id, path, owner,  description, published FROM '
                           + VCSFavoriteDBManager._schema_name + ' WHERE id = %s', (int_id,))
        row = cursor.fetchone()
        if row:
            return VCSFavorite(env, db_row=row)

        return None

    @classmethod
    def select_all(cls, env):
        favorites = []
        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, path, owner, description, published FROM '
                       + VCSFavoriteDBManager._schema_name)

        for row in cursor:
            favorites.append(VCSFavorite(env, db_row=row))

        return favorites

    @classmethod
    def select_all_owned_by(cls, env, owner):
        favorites = []
        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, path, owner, description, published FROM '
                       + VCSFavoriteDBManager._schema_name + ' WHERE owner= %s', (owner,))

        for row in cursor:
            favorites.append(VCSFavorite(env, db_row=row))

        return favorites

    @classmethod
    def select_all_user_viewable(cls, env, user=None):
        favorites = []
        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, path, owner, description, published'
                       + ' FROM ' + VCSFavoriteDBManager._schema_name
                       + ' WHERE owner= %s OR published=1', (user,))

        for row in cursor:
            favorites.append(VCSFavorite(env, db_row=row))

        return favorites

    @classmethod
    def select_all_path_begins_with(cls, env, starts_with):
        favorites = []
        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute(('SELECT id, path, owner, description, published'
                        + ' FROM ' + VCSFavoriteDBManager._schema_name
                        + ' WHERE ( path ' + db.like()
                        + ' OR path ' + db.like()
                        + ' OR path ' + db.like()
                        + ' )')
                       , (db.like_escape(starts_with) + '%',
                          db.like_escape(starts_with + '/') + '%',
                          db.like_escape(starts_with[:-1] if starts_with[-1:] == '/' else starts_with) + '%',
                          )
                       )
        print len(cursor.rows)
        for row in cursor:
            favorites.append(VCSFavorite(env, db_row=row))

        return favorites

    @classmethod
    def remove_one_by_path(cls, path, env):
#         try:
#             int_id = int(_id)
#         except ValueError:
#             env.log.error("%s is not an integer. Potential Sql injection atempt" % _id)
        rowcount = 0
        #paths is only stored with out trailing /
        path = path[:-1] if path[-1:] == '/' else path
        @with_transaction(env)
        def _do_remove_one(db):
            cursor = db.cursor()
            cursor.execute('DELETE FROM ' + VCSFavoriteDBManager._schema_name
                           + ' WHERE path = %s', (path,))
            rowcount = cursor.rowcount
        return rowcount

    @classmethod
    def remove_one_by_id(cls, _id, env):
        try:
            int_id = int(_id)
        except ValueError:
            env.log.error("%s is not an integer. Potential Sql injection atempt" % _id)
        rowcount = 0
        @with_transaction(env)
        def _do_remove_one(db):
            cursor = db.cursor()
            cursor.execute('DELETE FROM ' + VCSFavoriteDBManager._schema_name
                           + ' WHERE id = %s', (_id,))
            rowcount = cursor.rowcount
        return rowcount

    @classmethod
    def remove_list_by_id(cls, favorites, env):
        """
        Removes a list of id from favorites.
        """
        nr_rows = 0
        @with_transaction(env)
        def _do_remove_list(db):
            for _id in favorites:
                nr_rows =+ cls.remove_one_by_id(_id, env)
        return nr_rows

    @classmethod
    def remove_list_by_path(cls, favorites, env):
        """
        Removes a list of paths from favorites.
        """
        nr_rows = 0
        @with_transaction(env)
        def _do_remove_list(db):
            for path in favorites:
                nr_rows =+ cls.remove_one_by_path(path, env)
        return nr_rows
