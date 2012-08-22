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
    'hosts' : ['ec2-184-73-106-77.compute-1.amazonaws.com'],
    'key_path' : '~/raphaelcruzeiro.pem',
    'user' : 'ubuntu',
    'password' : '',
    'project_name' : 'test',
    'db_password' : 'super3360',
    'manage_py_path' : 'src',
    'settings_path' : 'src/test',
}

env.key_filename = config['key_path']
env.hosts = config['hosts']
env.user = config['user']
env.project_name = config['project_name']
env.db_password = config['db_password']
env.project_path = '/srv/www/%s' % env.project_name
env.application_path = '/srv/www/%s/application/%s' % (env.project_name, config['manage_py_path'])
env.virtualenv_path = '%s/bin/activate' % env.project_path

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
    out = run('sudo -u postgres psql -c "%s"' % sql)
    if show:
       print_command(sql)
    return out

def pip(modules):
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
    with cd('%s/bin/' % env.project_path):
        with prefix("source %s/bin/activate" % env.project_path):
            yield


@contextmanager
def project():
    """
    Run commands within the project's directory.
    """
    with virtualenv():
        with cd(env.application_path):
            yield

@log_call
def generate_ssh_key():
    run('ssh-keygen -t rsa')
    run('cat ~/.ssh/id_rsa.pub')

@log_call
def install_aptitude():
    sudo('apt-get install aptitude')

@log_call
def upgrade():
    sudo('aptitude update -y')
    sudo('aptitude upgrade -y')

@log_call
def install_base():
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

    sudo('easy_install pip')
    sudo('pip install virtualenv mercurial')

@log_call
def _create_database(name, password):
    psql("CREATE USER %s WITH ENCRYPTED PASSWORD '%s';" % (name, password))
    psql("CREATE DATABASE %s WITH OWNER %s ENCODING='UTF8';" % (env.project_name, env.project_name))

@log_call
def create_database():
    _create_database(env.project_name, env.db_password)

@log_call
def create():
    sudo('chown %s /srv' % env.user)
    with cd('/srv'):
        run('mkdir www')
    with cd('/srv/www'):
        run("virtualenv %s --distribute" % env.project_name)

    pip('django simplejson pytz PIL python-memcached south psycopg2 django-ses')

