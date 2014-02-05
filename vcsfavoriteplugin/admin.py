from trac.core import Component, implements, TracError
from trac.admin.api import IAdminPanelProvider
from trac.web.chrome import ITemplateProvider, add_script_data
from trac.util.translation import _
from trac.web.chrome import add_script
from vcsfavoriteplugin.model import VCSFavorite
from trac.web.chrome import add_notice
from trac.perm import PermissionError

class VCSFavoriteAdmin(Component):

    implements(ITemplateProvider, IAdminPanelProvider)


    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('vcsfavoriteplugin', resource_filename(__name__, 'htdocs'))]

    #IAdminPanelProvider
    def get_admin_panels(self, req):
        if 'REPOSITORY_ADMIN' in req.perm:
            yield ('versioncontrol', _("Version Control"),'favorites',_("Favorites"))

    def is_authorized(self, req ,owner):
        if req.authname != owner and not req.perm.has_permission('TRAC_ADMIN'):
            raise PermissionError(msg='You are not a trac admin or the owner of this favorite')

    def render_admin_panel(self, req, cat, page, url_favorite_id):

        edit = False
        selected_favorite = None

        #If it specifies favorite id it is in edit mode.
        if url_favorite_id:
            try:
                favorite_id = int(url_favorite_id)
            except Exception:
                raise TracError('No favorite with that id found.')

            edit = True
            if req.perm.has_permission('TRAC_ADMIN'):
                selected_favorite = VCSFavorite.select_one(favorite_id, self.env)
            else:
                selected_favorite = VCSFavorite.select_one(favorite_id, self.env,owner=req.authname)
            if not selected_favorite:
                raise TracError('No favorite with that id found.')

        #If form is posted
        if req.method == 'POST':
            if req.args.get('remove'):
                req.perm.require('TRAC_ADMIN')
                sel = req.args.get('del_sel')
                if not sel:
                    raise TracError(_('No favorites selected'))
                if not isinstance(sel, list):
                    sel = [int(sel)]
                else:
                    try:
                        for i,item in enumerate(sel):
                            sel[i] = int(sel[i])
                    except ValueError:
                        self.env.log.error("%s selected. Potential Sql injection atempt" % sel)
                        raise TracError(_('Internal error'))

                VCSFavorite.remove_list_by_id(sel, self.env)
                add_notice(req, _('The selected favorite have been '
                                  'removed.'))
                req.redirect(req.href.admin(cat, page))
            elif req.args.get('add'):
                req.perm.require('TRAC_ADMIN')
                path = req.args.get('favorite_path')
                desc = req.args.get('description')
                if req.args.get('add'):
                    favorite = VCSFavorite(self.env, path=path, description=desc, owner=req.authname)
                    favorite.insert()
                    add_notice(req, _('Favorite created.'))

            elif req.args.get('edit'):
                req.perm.require('TRAC_ADMIN')
                self.is_authorized(req, selected_favorite.owner)
                selected_favorite.path = req.args.get('favorite_path')
                selected_favorite.description = req.args.get('description')
                selected_favorite.update()
                add_notice(req, _('Favorite saved.'))
                #Redirect back to vcs favorite main page
                req.redirect(req.href.admin(cat, page))
            elif req.args.get('cancel') and selected_favorite:
                req.redirect(req.href.admin(cat, page))

        #Prepare data
        if req.perm.has_permission('TRAC_ADMIN'):
            vcs_favorites = VCSFavorite.select_all(self.env)
        else:
            vcs_favorites = VCSFavorite.select_all_user_viewable(self.env,user=req.authname)
        trac_base_url = req.href() + "/" if req.href() != "/" else "/"
        add_script_data(req, {'tracBaseUrl': trac_base_url})
        add_script(req,'vcsfavoriteplugin/js/vcs_favorite_admin.js')
        add_script(req,'vcsfavoriteplugin/js/jquery-ui.js')
        return ('vcs_favorite_admin.html',
                 {'vcs_favorites': vcs_favorites,
                  'edit': edit,
                  'favorite': selected_favorite,})
