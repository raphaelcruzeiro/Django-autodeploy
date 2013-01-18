import os
import sys
from functools import wraps
from getpass import getpass, getuser
from glob import glob
from contextlib import contextmanager

from fabric.api import env, cd, prefix, sudo as _sudo, run as _run, hide
from fabric.contrib.files import exists, upload_template
from fabric.colors import yellow, green, blue, red

###########
# Config  #
###########

config = {
    'server_name' : 'ec2-23-22-71-51.compute-1.amazonaws.com',
    'hosts' : ['ec2-23-22-71-51.compute-1.amazonaws.com'],
    'key_path' : '~/keys/inspira.pem',
    'user' : 'ubuntu',
    'password' : '',
    'project_name' : 'test',
    'db_password' : 'super3360',
    'manage_py_path' : '',
    'settings_path' : '',
    'repository_type' : 'git',
    'repository_url' : 'git@bitbucket.org:inspira_tecnologia/inspira_site.git',
    'gunicorn_port' : '8000',
    'aws_key' : '',
    'aws_secret' : ''
}

env.server_name = config['server_name']
env.key_filename = config['key_path']
env.hosts = config['hosts']
env.user = config['user']
env.project_name = config['project_name']
env.db_password = config['db_password']
env.project_path = '/srv/www/%s' % env.project_name
env.application_path = '/srv/www/%s/%s' % (env.project_name, config['manage_py_path'])
env.virtualenv_path = '%s/env/bin/activate' % env.project_path
env.repository_type = config['repository_type']
env.repository_url = config['repository_url']
env.manage = "%s/bin/python %s/manage.py" % (env.project_path, env.application_path)
env.gunicorn_port = config['gunicorn_port']
env.settings_path = env.application_path if not len(config['settings_path']) else '%s/%s' % (env.application_path, config['settings_path'])
env.aws_key = config['aws_key']
env.aws_secret = config['aws_secret']

templates = {
    'django_settings' : {
        'local_path' : 'templates/live_settings.py',
        'remote_path' : '%s/local_settings.py' % env.settings_path
    },
    'gunicorn' : {
        'local_path' : 'templates/gunicorn.conf.py',
        'remote_path' : env.project_path
    },
    'nginx' : {
        'local_path' : 'templates/nginx.conf',
        'remote_path' : '/etc/nginx/sites-enabled/%s.conf' % env.project_name,
        'reload_command' : '/etc/init.d/nginx restart'
    }
}

def _print(output):
    print
    print output
    print


def print_command(command):
    _print(blue("$ ", bold=True) +
           yellow(command, bold=True) +
           red(" ->", bold=True))


def run(command, show=True):
    """
    Run a shell comand on the remote server.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _run(command)


def sudo(command, show=True):
    """
    Run a command as sudo.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _sudo(command)

def psql(sql, show=True):
    """
    Executes a psql command
    """
    out = run('sudo -u postgres psql -c "%s"' % sql)
    if show:
       print_command(sql)
    return out

def pip(modules):
    """
    Install the Python modules passed as arguments with pip
    """
    with virtualenv():
        run('pip install %s' % modules)

def log_call(func):
    @wraps(func)
    def logged(*args, **kawrgs):
        header = "-" * len(func.__name__)
        _print(green("\n".join([header, func.__name__, header]), bold=True))
        return func(*args, **kawrgs)
    return logged

@contextmanager
def virtualenv():
    """
    Run commands within the project's virtualenv.
    """
    with cd('%s/env/bin/' % env.project_path):
        with prefix("source %s/env/bin/activate" % env.project_path):
            yield


@contextmanager
def project():
    """
    Run commands within the project's directory.
    """
    with virtualenv():
        with cd(env.application_path):
            yield

def manage(command):
    """
    Run a Django management command.
    """
    return run("%s %s" % (env.manage, command))

@log_call
def generate_ssh_key():
    """
    Generates a key pair and displays the public key
    """
    run('ssh-keygen -t rsa')
    run('cat ~/.ssh/id_rsa.pub')

@log_call
def install_aptitude():
    sudo('apt-get install aptitude -y')

@log_call
def upgrade():
    """
    Updates the repository definitions and upgrades the server
    """
    sudo('aptitude update -y')
    sudo('aptitude upgrade -y')

def upload_template_and_reload(name):
    template_settings = templates[name]
    local_path = template_settings['local_path']
    remote_path = template_settings['remote_path']
    reload_command = template_settings.get('reload_command')
    owner = template_settings.get("owner")
    mode = template_settings.get("mode")

    print '%s to %s' % (local_path, remote_path)

    upload_template(local_path, remote_path, env, use_sudo=True)

    if owner:
        sudo("chown %s %s" % (owner, remote_path))
    if mode:
        sudo("chmod %s %s" % (mode, remote_path))

    if reload_command:
        sudo(reload_command)


@log_call
def install_base():
    """
    Installs the base software required to deploy an application
    """
    install_aptitude()
    sudo('aptitude install gcc make git-core nginx postgresql memcached python-dev python-setuptools supervisor postgresql-server-dev-all  -y')

    run('wget http://www.ijg.org/files/jpegsrc.v8d.tar.gz')
    run('tar xvzf jpegsrc.v8d.tar.gz')
    with cd('jpeg-8d'):
        run('./configure')
        run('make')
        sudo('make install')

    run('wget http://download.savannah.gnu.org/releases/freetype/freetype-2.4.10.tar.gz')
    run('tar xvzf freetype-2.4.10.tar.gz')
    with cd('freetype-2.4.10'):
        run('./configure')
        run('make')
        sudo('make install')

    run('wget http://zlib.net/zlib-1.2.7.tar.gz')
    run('tar xvzf zlib-1.2.7.tar.gz')
    with cd('zlib-1.2.7'):
        run('./configure')
        run('make')
        sudo('make install')

    sudo('easy_install pip')
    sudo('pip install virtualenv mercurial')

@log_call
def _create_database(name, password):
    psql("CREATE USER %s WITH ENCRYPTED PASSWORD '%s';" % (name, password))
    psql("CREATE DATABASE %s WITH OWNER %s ENCODING='UTF8';" % (env.project_name, env.project_name))

@log_call
def create_database():
    """
    Creates a database and a database user with the project name and the specified password
    """
    _create_database(env.project_name, env.db_password)

@log_call
def create():
    """
    Stages the application on the server
    """
    sudo('chown %s /srv' % env.user)
    with cd('/srv'):
        run('mkdir www')
    with cd('/srv/www'):
        run('%s clone %s %s' %(env.repository_type, env.repository_url, env.project_path))

    with cd(env.project_path):
        run("virtualenv env --distribute")
        with virtualenv():
            run('pip install -r %s/requirements' % env.project_path)

    upload_template_and_reload('django_settings')
    upload_template_and_reload('gunicorn')
    upload_template_and_reload('nginx')

    manage('syncdb')


