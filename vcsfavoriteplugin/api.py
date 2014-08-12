from trac.versioncontrol.api import RepositoryManager, NoSuchNode
from trac.web.api import IRequestHandler
from trac.core import Component, implements, TracError
import posixpath
from trac.util.presentation import to_json
from trac.util import embedded_numbers, pathjoin
from vcsfavoriteplugin.model import VCSFavorite
from trac.util.translation import _
from trac.web.chrome import ITemplateProvider
from pkg_resources import resource_filename


class FavoritesAndSuggestionPathSearch(Component):

    implements(IRequestHandler, ITemplateProvider)

    # ITemplateProvider methods
    def get_templates_dirs(self):
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        return [('vcsfavoriteplugin', resource_filename(__name__, 'htdocs'))]

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == '/vcsfavorites'

    def process_request(self, req):

        q = req.args.get('q')
        dirname, prefix = posixpath.split(q)
        prefix = prefix.lower()

        def kind_order(entry):
            return (not entry['id'], embedded_numbers(entry['id']))

        bm_entries = {'text': _('Favorites'),
                      'children': [],
                      }
        result = []

        # if no query then we only need to return the favorites.
        if not q:
            bm_entries['children'].extend({'id': bm.path,
                                           'text': bm.path,
                                           'is_favorite': True
                                           } for bm in VCSFavorite.select_all(self.env)
                                          )
            bm_entries['children'] = sorted(bm_entries['children'], key=kind_order)
            result.append(bm_entries)
            json = to_json(result)
            req.send(json, 'text/json')
            return

        repo_entries = self._get_vcs_folders(req, q, dirname, prefix)

        bm_entries['children'].extend({'id': bm.path,
                                       'text': bm.path,
                                       'is_favorite': True
                                       } for bm in VCSFavorite.select_all_path_begins_with(self.env, q)
                                      )

        for b_entry in bm_entries['children']:
            for r_entry in repo_entries['children']:
                if r_entry['text'] == b_entry['text'] or r_entry['text'] == (b_entry['text'] + '/'):
                    r_entry['is_favorite'] = True
                    break

        bm_entries['children'] = sorted(bm_entries['children'], key=kind_order)
        repo_entries['children'] = sorted(repo_entries['children'], key=kind_order)
        if bm_entries['children']:
            result.append(bm_entries)
        if repo_entries['children']:
            result.append(repo_entries)
        json = to_json(result)
        req.send(json, 'text/json')

    def _get_vcs_folders(self, req, q, dirname, prefix):
        rm = RepositoryManager(self.env)

        reponame, repos, path = rm.get_repository_by_path(dirname)
        repo_entries = {'text': _('Suggestions'),
                        'children': [],
                        }

        # Removes the reponame from path if it's the default alias.
        # TODO: Remove this as part of #4755
        default_repo_alias = self.env.config.get('repositories', '.alias')
        if repos.reponame == default_repo_alias:
            reponame = ''
        else:
            reponame = repos.reponame

        if repos:
            try:
                entries = ({'id': '/' + pathjoin(reponame, e.path),
                           'text': '/' + pathjoin(reponame, e.path),
                           'is_favorite': False
                            }
                           for e in repos.get_node(path).get_entries()
                           if e.can_view(req.perm)
                           and e.name.lower().startswith(prefix)
                           and e.isdir
                           )
                repo_entries['children'].extend(entries)

                if q.endswith('/'):
                    repo_entries['children'].append({'id': q,
                                                     'text': q,
                                                     'is_favorite': False
                                                     }
                                                    )
            except NoSuchNode:
                pass
        return repo_entries


class AddFavorite(Component):
    implements(IRequestHandler)

    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info == '/vcsfavorites/add'

    def process_request(self, req):
        path = req.args.get('path')
        favorite = VCSFavorite(self.env, path=path)
        favorite.insert()
        req.send('', 'text/plain')


class RemoveFavorite(Component):
    implements(IRequestHandler)

    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info == '/vcsfavorites/remove'

    def process_request(self, req):
        path = req.args.get('path')
        VCSFavorite.remove_one_by_path(path, self.env)
        req.send('', 'text/plain')
