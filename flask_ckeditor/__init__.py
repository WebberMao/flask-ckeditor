# -*- coding: utf-8 -*-
"""
    flask_ckeditor
    ~~~~~~~~~~~~~~~

    :author: Grey Li <withlihui@gmail.com>
    :copyright: (c) 2020 by Grey Li.
    :license: MIT, see LICENSE for more details.
"""
import warnings
from functools import wraps
from flask import current_app, Markup, Blueprint, url_for, request, jsonify, render_template_string

from flask_ckeditor.fields import CKEditorField  # noqa
from flask_ckeditor.utils import get_url, random_filename  # noqa


class _CKEditor4(object):
    """The class implement functions for Jinja2 template."""

    @staticmethod
    def load(custom_url=None, pkg_type=None, serve_local=None, version='4.14.0'):
        """Load CKEditor resource from CDN or local.

        :param custom_url: The custom resource url to use, build your CKEditor
            on `CKEditor builder <https://ckeditor.com/cke4/builder>`_.
        :param pkg_type: The type of CKEditor package, one of ``basic``,
            ``standard`` and ``full``. If you serve the package from CDN, you can
            also pass ``standard-all`` and ``full-all``. Default to ``standard``.
            It's a mirror argument to overwrite ``CKEDITOR_PKG_TYPE``.
        :param serve_local: Mirror argument to overwrite ``CKEDITOR_SERVE_LOCAL``.
        :param version: The version of CKEditor.
        """
        pkg_type = pkg_type or current_app.config['CKEDITOR_PKG_TYPE']
        serve_local = serve_local or current_app.config['CKEDITOR_SERVE_LOCAL']
        local_preset_list = ['basic', 'standard', 'full']
        cdn_preset_list = local_preset_list + ['standard-all', 'full-all']

        if serve_local and pkg_type not in local_preset_list:
            warnings.warn('The provided pkg_type string was invalid, '
                          'it should be one of basic/standard/full.')
            pkg_type = 'standard'
        if not serve_local and pkg_type not in cdn_preset_list:
            warnings.warn('The provided pkg_type string was invalid, '
                          'it should be one of basic/standard/standard-all/full/full-all.')
            pkg_type = 'standard'

        if serve_local:
            url = url_for('ckeditor.static', filename='%s/ckeditor.js' % pkg_type)
        else:
            if current_app.config['CKEDITOR_ENABLE_CODESNIPPET'] and not pkg_type.endswith('all'):
                warnings.warn('The CodeSnippet plugin only included in standard-all/full-all pakcage.')
                pkg_type = 'standard-all'
            url = 'https://cdn.ckeditor.com/%s/%s/ckeditor.js' % (version, pkg_type)

        if custom_url:
            url = custom_url
        return Markup('<script src="%s"></script>' % url)

    @staticmethod  # noqa
    def config(name='ckeditor', custom_config='', **kwargs):
        """Config CKEditor.

        :param name: The target input field's name. If you use Flask-WTF/WTForms, it need to set
            to field's name. Default to ``'ckeditor'``.
        :param custom_config: The addition config, for example ``uiColor: '#9AB8F3'``.
            The proper syntax for each option is ``configuration name : configuration value``.
            You can use comma to separate multiple key-value pairs. See the list of available
            configuration settings on
            `CKEditor documentation <https://docs.ckeditor.com/ckeditor4/docs/#!/api/CKEDITOR.config>`_.
        :param kwargs: Mirror arguments to overwritten configuration variables, see docs for more details.

        .. versionadded:: 0.3
        """
        extra_plugins = kwargs.get('extra_plugins', current_app.config['CKEDITOR_EXTRA_PLUGINS'])

        file_uploader = kwargs.get('file_uploader', current_app.config['CKEDITOR_FILE_UPLOADER'])
        file_browser = kwargs.get('file_browser', current_app.config['CKEDITOR_FILE_BROWSER'])

        if file_uploader != '':
            file_uploader = get_url(file_uploader)
        if file_browser != '':
            file_browser = get_url(file_browser)

        if file_uploader or file_browser and 'filebrowser' not in extra_plugins:
            extra_plugins.append('filebrowser')

        language = kwargs.get('language', current_app.config['CKEDITOR_LANGUAGE'])
        height = kwargs.get('height', current_app.config['CKEDITOR_HEIGHT'])
        width = kwargs.get('width', current_app.config['CKEDITOR_WIDTH'])

        code_theme = kwargs.get('code_theme', current_app.config['CKEDITOR_CODE_THEME'])

        wrong_key_arg = kwargs.get('codesnippet', None)
        if wrong_key_arg:
            warnings.warn('Argument codesnippet was renamed to enable_codesnippet and will be removed in future.')

        enable_codesnippet = kwargs.get('enable_codesnippet', wrong_key_arg) or \
            current_app.config['CKEDITOR_ENABLE_CODESNIPPET']

        if enable_codesnippet and 'codesnippet' not in extra_plugins:
            extra_plugins.append('codesnippet')

        enable_csrf = kwargs.get('enable_csrf', current_app.config['CKEDITOR_ENABLE_CSRF'])

        if enable_csrf:
            if 'csrf' not in current_app.extensions:
                raise RuntimeError("CSRFProtect is not initialized. It's required to enable CSRF protect, \
                    see docs for more details.")
            csrf_header = render_template_string('''
                fileTools_requestHeaders: {
                    'X-CSRFToken': '{{ csrf_token() }}',
                },''')
        else:
            csrf_header = ''

        return Markup('''
<script type="text/javascript">
    document.getElementById("%s").classList.remove("ckeditor");
    CKEDITOR.replace( "%s", {
        language: "%s",
        height: %s,
        width: %s,
        codeSnippet_theme: "%s",
        imageUploadUrl: "%s",
        filebrowserUploadUrl: "%s",
        filebrowserBrowseUrl: "%s",
        extraPlugins: "%s",
        %s // CSRF token header for XHR request
        %s
    });
</script>''' % (
            name, name, language, height, width, code_theme, file_uploader, file_uploader, file_browser,
            ','.join(extra_plugins), csrf_header, custom_config))

    @staticmethod
    def create(name='ckeditor', value=''):
        """Create a ckeditor textarea directly.

        :param name: The name attribute of CKEditor textarea, set it when you need to create
            more than one textarea in one page. Default to ``ckeditor``.
        :param value: The preset value for textarea.

        .. versionadded:: 0.3
        .. versionchanged:: 0.4.5
            The value of ``name`` will be used as ``id`` attribute.
        """
        return Markup('<textarea class="ckeditor" name="%s" id="%s">%s</textarea>' % (name, name, value))

    @staticmethod
    def load_code_theme():
        """Highlight the code snippets.

        .. versionadded:: 0.3
        """
        theme = current_app.config['CKEDITOR_CODE_THEME']
        pkg_type = current_app.config['CKEDITOR_PKG_TYPE']
        js_url = url_for('ckeditor.static',
                         filename='%s/plugins/codesnippet/lib/highlight/highlight.pack.js' % pkg_type)
        css_url = url_for('ckeditor.static',
                          filename='%s/plugins/codesnippet/lib/highlight/styles/%s.css' % (pkg_type, theme))
        return Markup('''<link href="%s" rel="stylesheet">\n<script src="%s"></script>\n
            <script>hljs.initHighlightingOnLoad();</script>''' % (css_url, js_url))


class _CKEditor5(object):
    """The class implement functions for Jinja2 template."""

    def __init__(self):
        self.editor_dict = {'classic':'ClassicEditor',
                        'inline':'InlineEditor', 
                        'balloon':'BalloonEditor',
                        'balloon-block':'BalloonEditor',
                        'decoupled-document':'DecoupledEditor'}

    def check_editor_type(self, editor_type):
        editor_type = editor_type or current_app.config['CKEDITOR_EDITOR_TYPE']
        if editor_type not in self.editor_dict.keys():
            warnings.warn('The provided editor_type string was invalid, '
                          'it should be one of classic/inline/balloon/balloon-block/decoupled-document.')
            editor_type = 'classic'
        return editor_type

    def extra_plugin(self, file_uploader=None):
        plugin = []

        if file_uploader is not None:
            plugin.append('''ckfinder:{uploadUrl: "%s"}''' % (file_uploader))

        return ',\n\t\t\t'.join(plugin)
       

    def load(self, custom_url=None, editor_type=None, serve_local=None, version='28.0.0'):
        """Load CKEditor resource from CDN or local."""

        self.editor_type = self.check_editor_type(editor_type)
        url = 'https://cdn.ckeditor.com/ckeditor5/%s/%s/ckeditor.js' % (version, self.editor_type)

        if custom_url:
            url = custom_url

        return Markup('<script src="%s"></script>' % url)

    def config(self, name='ckeditor', custom_config='', **kwargs):
        """Config CKEditor."""


        file_uploader = kwargs.get('file_uploader', current_app.config['CKEDITOR_FILE_UPLOADER'])

        if file_uploader != '':
            file_uploader = get_url(file_uploader)

        plugin = self.extra_plugin(file_uploader)

        return Markup('''
                        <script type="text/javascript">                                                     
        %s                                                                                  
        .create(document.querySelector( "%s" ), { 
            %s 
        })                                 
        .then( ckeditor => {                                                                
                window.ckeditor = ckeditor;                                                 
                const toolbarContainer = document.querySelector( '#ckeditor-toolbox' );
                toolbarContainer.appendChild( ckeditor.ui.view.toolbar.element );
        })
        .catch( error => {
                console.error( error );
        });
        document.querySelector( '#submit' ).addEventListener( 'click', () => {
                document.getElementById( "%s" ).value = window.ckeditor.getData();
        });
                        </script> ''' % (self.editor_dict[self.editor_type], '#'+name+'_', plugin, name))

    @staticmethod
    def create(name='ckeditor', value=''):
        """Create a ckeditor textarea directly."""
        return Markup('<textarea hidden name="%s" id="%s"></textarea><div id="ckeditor_toolbox"></div><div name="%s" id="%s">%s</div>' % (name, name, name+'_', name+'_', value))



class CKEditor4(object):
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        blueprint = Blueprint('ckeditor', __name__,
                              static_folder='static', static_url_path='/ckeditor' + app.static_url_path)
        app.register_blueprint(blueprint)

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['ckeditor'] = _CKEditor4()
        app.context_processor(self.context_processor)

        app.config.setdefault('CKEDITOR_SERVE_LOCAL', False)
        app.config.setdefault('CKEDITOR_PKG_TYPE', 'standard')

        app.config.setdefault('CKEDITOR_LANGUAGE', '')
        app.config.setdefault('CKEDITOR_HEIGHT', 0)
        app.config.setdefault('CKEDITOR_WIDTH', 0)
        app.config.setdefault('CKEDITOR_CODE_THEME', 'monokai_sublime')

        app.config.setdefault('CKEDITOR_FILE_UPLOADER', '')
        app.config.setdefault('CKEDITOR_FILE_BROWSER', '')

        # Default error message for upload fail
        # .. versionadded:: 0.4.0
        app.config.setdefault('CKEDITOR_UPLOAD_ERROR_MESSAGE', 'Upload failed.')

        # Enable Code Snippet plugin
        # .. versionadded:: 0.4.0
        app.config.setdefault('CKEDITOR_ENABLE_CODESNIPPET', False)

        # Register extra CKEditor plugins
        # .. versionadded:: 0.3.4
        app.config.setdefault('CKEDITOR_EXTRA_PLUGINS', [])

        # Add CSRF protect support for image uplaoding
        # .. versionadded:: 0.4.3
        app.config.setdefault('CKEDITOR_ENABLE_CSRF', False)

    @staticmethod
    def context_processor():
        return {'ckeditor': current_app.extensions['ckeditor']}

    @staticmethod
    def uploader(func):
        """This method only used for CKEditor under version 4.5, in newer version,
        you should use ``upload_success()`` and ``upload_fail()`` instead.

        Decorated the view function that handle the file upload. The upload
        view must return the uploaded image's url. For example::

            from flask import send_from_directory

            app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'  # this value can be endpoint or url


            @app.route('/files/<filename>')
            def uploaded_files(filename):
                path = '/the/uploaded/directory'
                return send_from_directory(path, filename)

            @app.route('/upload', methods=['POST'])
            @ckeditor.uploader
            def upload():
                f = request.files.get('upload')
                f.save(os.path.join('/the/uploaded/directory', f.filename))
                url = url_for('uploaded_files', filename=f.filename)
                return url

        .. versionadded:: 0.3
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            func_num = request.args.get('CKEditorFuncNum')
            # ckeditor = request.args.get('CKEditor')
            # language code used for error message, not used yet.
            # lang_code = request.args.get('langCode')
            # the error message to display when upload failed.
            message = current_app.config['CKEDITOR_UPLOAD_ERROR_MESSAGE']
            url = func(*args, **kwargs)
            return Markup('''<script type="text/javascript">
        window.parent.CKEDITOR.tools.callFunction(%s, "%s", "%s");</script>''' % (func_num, url, message))

        return wrapper


class CKEditor5(CKEditor4):
    def __init__(self, app=None):
        super(CKEditor5, self).__init__(app)

    def init_app(self, app):
        blueprint = Blueprint('ckeditor', __name__,
                              static_folder='static', static_url_path='/ckeditor' + app.static_url_path)
        app.register_blueprint(blueprint)

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        
        app.extensions['ckeditor'] = _CKEditor5()

        app.context_processor(self.context_processor)

        app.config.setdefault('CKEDITOR_EDITOR_TYPE', 'classic')

        app.config.setdefault('CKEDITOR_FILE_UPLOADER', '')

        # Default error message for upload fail
        # .. versionadded:: 0.4.0
        app.config.setdefault('CKEDITOR_UPLOAD_ERROR_MESSAGE', 'Upload failed.')



def upload_success(url, filename='', message=None):
    """Return a upload success response, for CKEditor >= 4.5.
    For example::

        from flask import send_from_directory
        from flask_ckeditor import upload_success

        app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'  # this value can be endpoint or url


        @app.route('/files/<path:filename>')
        def uploaded_files(filename):
            path = '/the/uploaded/directory'
            return send_from_directory(path, filename)

        @app.route('/upload', methods=['POST'])
        def upload():
            f = request.files.get('upload')
            f.save(os.path.join('/the/uploaded/directory', f.filename))
            url = url_for('uploaded_files', filename=f.filename)
            return upload_success(url=url)  # <--

    :param url: the URL of uploaded image.
    :param filename: the filename of uploaded image, optional.
    :param message: the warning message displayed to the user, optional. 

    .. veresionchanged:: 0.4.7
       Add new parameter ``message``.

    .. versionadded:: 0.4.0
    """
    data = {'uploaded': 1, 'url': url, 'filename': filename}
    if message is not None:
        data['error'] = {'message': message}
    return jsonify(data)


def upload_fail(message=None):
    """Return a upload failed response, for CKEditor >= 4.5.
    For example::

        from flask import send_from_directory
        from flask_ckeditor import upload_success, upload_fail

        app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'  # this value can be endpoint or url


        @app.route('/files/<path:filename>')
        def uploaded_files(filename):
            path = '/the/uploaded/directory'
            return send_from_directory(path, filename)

        @app.route('/upload', methods=['POST'])
        def upload():
            f = request.files.get('upload')
            if extension not in ['jpg', 'gif', 'png', 'jpeg']:
                return upload_fail(message='Image only!')  # <--
            f.save(os.path.join('/the/uploaded/directory', f.filename))
            url = url_for('uploaded_files', filename=f.filename)
            return upload_success(url=url)

    :param message: error message.

    .. versionadded:: 0.4.0
    """
    if message is None:
        message = current_app.config['CKEDITOR_UPLOAD_ERROR_MESSAGE']
    return jsonify(uploaded=0, error={'message': message})
