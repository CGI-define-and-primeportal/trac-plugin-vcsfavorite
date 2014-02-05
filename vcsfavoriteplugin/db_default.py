from trac.db import Table, Column, Index

__all__ = ['name', 'version', 'schemas']

name = 'vcs_favorites'
version = 1
schemas = [Table(name, key='id')[Column('id', auto_increment=True),
                                     Column('path', 'text'),
                                     Column('owner', 'text'),
                                     Column('description', 'text'),
                                     Column('published', 'int'),
                                     Index(['path'], unique=True)],]
