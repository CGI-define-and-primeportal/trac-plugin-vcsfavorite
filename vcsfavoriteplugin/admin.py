from trac.core import Component, implements, TracError
from trac.admin.api import IAdminPanelProvider
from trac.web.chrome import ITemplateProvider, add_script_data
from trac.util.translation import _
from trac.web.chrome import add_script
from vcsfavoriteplugin.model import VCSFavorite
from trac.web.chrome import add_notice
from pkg_resources import resource_filename


class VCSFavoriteAdmin(Component):

    implements(ITemplateProvider, IAdminPanelProvider)

    # ITemplateProvider methods
    def get_templates_dirs(self):
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        return [('vcsfavoriteplugin', resource_filename(__name__, 'htdocs'))]

    #IAdminPanelProvider
    def get_admin_panels(self, req):
            yield ('versioncontrol', _("Version Control"), 'favorites', _("Favorites"))

    def render_admin_panel(self, req, cat, page, path_info):

        edit = False
        selected_favorite = None

        #If it specifies favorite id it is in edit mode.
        if path_info:
            try:
                favorite_id = int(path_info)
            except Exception:
                raise TracError('Malformed url. Favorite id not a number.')

            edit = True
            selected_favorite = VCSFavorite.select_one(favorite_id, self.env)
            if not selected_favorite:
                raise TracError('No favorite with that id found.')

        #If form is posted
        if req.method == 'POST':
            if req.args.get('remove'):
                sel = req.args.getlist('del_sel')
                if not sel:
                    raise TracError(_('No favorites selected'))
                try:
                    for i in xrange(len(sel)):
                        sel[i] = int(sel[i])
                except ValueError, e:
                    raise TracError(_('Internal error: ') + e.message)

                VCSFavorite.remove_list_by_id(sel, self.env)
                add_notice(req, _('The selected favorite'
                                  + ('s' if len(sel) > 1 else '')
                                  + ' has been '
                                  + 'removed.'))
                req.redirect(req.href.admin(cat, page))
            elif req.args.get('add'):
                path = req.args.get('favorite_path')
                desc = req.args.get('description')
                favorite = VCSFavorite(self.env, path=path, description=desc)
                favorite.insert()
                add_notice(req, _('Favorite created.'))

            elif req.args.get('edit'):
                selected_favorite.path = req.args.get('favorite_path')
                selected_favorite.description = req.args.get('description')
                selected_favorite.update()
                add_notice(req, _('Favorite saved.'))
                #Redirect back to vcs favorite main page
                req.redirect(req.href.admin(cat, page))
            elif req.args.get('cancel') and selected_favorite:
                req.redirect(req.href.admin(cat, page))

        #Prepare data
        vcs_favorites = VCSFavorite.select_all(self.env)
        trac_base_url = req.href() + "/" if req.href() != "/" else "/"
        add_script_data(req, {'tracBaseUrl': trac_base_url})
        add_script(req, 'vcsfavoriteplugin/js/vcs_favorite_admin.js')
        add_script(req, 'vcsfavoriteplugin/js/jquery-ui.js')
        return ('vcs_favorite_admin.html',
                {'vcs_favorites': vcs_favorites,
                 'edit': edit,
                 'favorite': selected_favorite,
                 }
                )
