Django Autodeploy
=================

What is this?
-------------

The Django Autodeploy Tool is a fabric script for creating a webserver for Django applications from scratch on a Debian-based box (It has been fully tested with Ubuntu Server). The script will also deploy the application and enable you tu fetch new versions from your repository and migrate the database, collect static files, etc with a single command run from your machine.

Usage
-----

Open the 'fabfile.py' and locate the config section. All you have to do is write your projects details there and the script will be ready to connect to the server.
If you don't have a ssh keypair you can generate it running the command ''fab generate_ssh_key'' and then all you have to do is to copy the public key from the output to your Github or Bitbucket profile.

To fully install your application and all the necessary software needed to run it, just run ''fab isntall_all''.
To fetch a new version from the repository and update you application, run ''fab fetch''.

