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

env.key_filename = '~/raphaelcruzeiro.pem'
env.hosts = ['ec2-184-73-106-77.compute-1.amazonaws.com']
env.user = 'ubuntu'
env.project_name = 'test'
env.db_password = 'super3360'

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

def log_call(func):
    @wraps(func)
    def logged(*args, **kawrgs):
        header = "-" * len(func.__name__)
        _print(green("\n".join([header, func.__name__, header]), bold=True))
        return func(*args, **kawrgs)
    return logged

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
    sudo('aptitude install gcc make git-core nginx postgresql memcached python-dev python-setuptools supervisor -y')
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
