from trac.db import Table, Column, Index

__all__ = ['name', 'version', 'schemas']

name = 'vcs_favorites'
version = 2
schemas = [Table('vcs_favorites', key='id')[Column('id', auto_increment=True),
                                     Column('path', 'text'),
                                     Column('description', 'text'),
                                     Index(['path'], unique=True)],]
