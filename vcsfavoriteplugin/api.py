from trac.versioncontrol.api import RepositoryManager, NoSuchNode
from trac.web.api import IRequestHandler
from trac.core import Component, implements, TracError
import posixpath
from trac.util.presentation import to_json
from trac.util import embedded_numbers, pathjoin
from vcsfavoriteplugin.model import VCSFavorite
from trac.util.translation import _

class FavoritesAndSuggestionPathSearch(Component):

    implements(IRequestHandler)

    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info == '/vcsfavorites'

    def process_request(self, req):
        if not req.get_header('X-Requested-With') == 'XMLHttpRequest':
            raise TracError('This resource works only with header X-Requested-With:XMLHttpRequest')

        rm = RepositoryManager(self.env)

        q = req.args.get('q')
        dirname, prefix = posixpath.split(q)
        prefix = prefix.lower()
        reponame, repos, path = rm.get_repository_by_path(dirname)

        def kind_order(entry):
            return (not entry['id'], embedded_numbers(entry['id']))

        repo_entries = {'text': _('Suggestions'),
                        'children': [],
                        }
        bm_entries = {'text': _('Favorites'),
                      'children': [],
                      }
        result = []

        # if no query then we only need to return the favorites.
        if not q:
            bm_entries['children'].extend({'id': bm.path, 'text': bm.path, 'is_favorite' : True}
                                      for bm in VCSFavorite.select_all(self.env))
            bm_entries['children'] = sorted(bm_entries['children'], key=kind_order)
            result.append(bm_entries)
            json = to_json(result)
            req.send(json,'text/json')
            return

        if repos:
            try:
                repo_entries['children'].extend({'id': '/' + pathjoin(repos.reponame, e.path),
                                                 'text': '/' + pathjoin(repos.reponame, e.path),
                                                 'is_favorite': False}
                                                for e in repos.get_node(path).get_entries()
                                                    if e.can_view(req.perm) and
                                                        e.name.lower().startswith(prefix) and
                                                        e.isdir)
                if q.endswith('/'):
                    repo_entries['children'].append({'id': q,
                                                     'text': q,
                                                     'is_favorite': False})
            except NoSuchNode:
                pass

        bm_entries['children'].extend({'id': bm.path,
                                       'text': bm.path,
                                       'is_favorite': True}
                                      for bm in VCSFavorite.select_all_path_begins_with(self.env, q))

        for b_entry in bm_entries['children']:
            for r_entry in repo_entries['children']:
                if r_entry['text'] == b_entry['text'] or r_entry['text'] == (b_entry['text'] + '/'):
                    r_entry['is_favorite'] = True
                    break;

        bm_entries['children'] = sorted(bm_entries['children'], key=kind_order)
        repo_entries['children'] = sorted(repo_entries['children'], key=kind_order)
        if bm_entries['children']:
            result.append(bm_entries)
        if repo_entries['children']:
            result.append(repo_entries)
        json = to_json(result)
        req.send(json,'text/json')

class AddFavorite(Component):
    implements(IRequestHandler)

    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info == '/vcsfavorites/add'

    def process_request(self, req):
        if not req.get_header('X-Requested-With') == 'XMLHttpRequest':
            raise TracError('This resource works only with header X-Requested-With:XMLHttpRequest')
        path = unicode(req.args.get('path'))
        favorite = VCSFavorite(self.env, path=path, owner=req.authname)
        favorite.insert()
        req.send('','text/plain')

class RemoveFavorite(Component):
    implements(IRequestHandler)

    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info == '/vcsfavorites/remove'

    def process_request(self, req):
        if not req.get_header('X-Requested-With') == 'XMLHttpRequest':
            raise TracError('This resource works only with header X-Requested-With:XMLHttpRequest')
        path = unicode(req.args.get('path'))
        VCSFavorite.remove_one_by_path(path, self.env)
        req.send('','text/plain')
