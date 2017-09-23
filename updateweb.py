#!/usr/bin/env python
### usage: fab -f update.py  get_version:source_type=web,source_dir=/var/lib/jenkins/workspace/alarm,name=app deploy
# by stark 

from fabric.api import *
from fabric.colors import *
from fabric.context_managers import *
from fabric.contrib.console import confirm
import datetime,sys,yaml
import sqlite3


#return Chinese time

env.today=(datetime.datetime.now()+datetime.timedelta(hours=13)).strftime('%Y%m%d')

env.source_type = ''
env.project_dev_source = ''
env.project_tar_source = ''
env.project_pack_name = ''
env.deploy_project_root = ''
env.deploy_release_dir = ''
env.deploy_name = ''
env.user = 'work'
env.hosts = []
env.password = '123456'

@task
@runs_once
def tar_source():

    with lcd(env.project_dev_source):
        # local("id && pwd")
        local("mkdir -p %s" %(env.project_tar_source))
        local("tar -czf %s.tar.gz -C %s %s --exclude=.svn" % (env.project_tar_source + env.project_pack_name,env.project_dev_source +'/'+ env.source_type, env.deploy_name))


@task
def put_package():

    env.deploy_full_path=env.deploy_project_root + env.deploy_release_dir + "/"+env.deploy_version
    run("mkdir -p %s" %(env.deploy_full_path))
    put(env.project_tar_source + env.project_pack_name +".tar.gz",env.deploy_full_path)
    ## check the MD5 of tar.gz
    lmd5=local("md5sum %s" %(env.project_tar_source + env.project_pack_name +".tar.gz"),capture=True).split(' ')[0]
    rmd5=run("md5sum %s" %(env.deploy_full_path + '/' + env.project_pack_name +".tar.gz")).split(' ')[0]
    if lmd5 == rmd5:
        print "MD5 OK!"
        with cd(env.deploy_full_path):
            run("tar -zxf %s.tar.gz" % (env.project_pack_name))
            run("rm -rf %s.tar.gz" % (env.project_pack_name))
    else:
        print "MD5 not OK!Please check or do it again!"
        print "local:  %s" %lmd5
        print "remote: %s" %rmd5
        sys.exit(-1)

@task
def make_symlink():
    env.deploy_full_path=env.deploy_project_root + env.deploy_release_dir + '/' + env.deploy_version +'/'+ env.deploy_name
    with settings(warn_only=True):
        run("ln -s %s %s" % (env.deploy_full_path, env.deploy_project_root + env.deploy_name +'.tmp'))
        run("mv -fT %s %s" %(env.deploy_project_root + env.deploy_name +'.tmp',env.deploy_project_root + env.deploy_name))


@hosts('localhost')
@task
def get_version(source_type,source_dir,name):

    with open("/var/lib/jenkins/scripts/hosts.yaml", 'r') as f:
        host_list = yaml.load(f)
        print host_list[name]
        env.hosts = host_list[name]
    env.source_type = source_type   
    env.project_dev_source = source_dir
    env.project_tar_source = source_dir + '/releases/'
    env.project_pack_name = name

    env.deploy_project_root = '/home/work/www/'
    env.deploy_release_dir = 'releases' 
    env.deploy_name = name


    conn = sqlite3.connect('/var/lib/jenkins/scripts/update.db')
    cursor = conn.cursor()
    cursor.execute("create table if not exists %s (id INTEGER primary key AUTOINCREMENT, version varchar(20))" % env.deploy_name)
    
    cursor.execute("select version from %s ORDER BY id DESC LIMIT 1" % env.deploy_name)
    values = cursor.fetchall()
    if len(values) == 0 :
        env.deploy_version=env.today+"v01"
        print env.deploy_version
    else:
        i = int(values[0][0][9:])
        # print values, type(values), i, type(i)
        if values[0][0][:8] != env.today:
            env.deploy_version=env.today+"v01"
        else:
            i+=1
            env.deploy_version=env.today+"v"+str(i).zfill(2)
            print env.deploy_version   


    cursor.close()
    conn.commit() 
    conn.close()

@task
def deploy():
    tar_source()
    put_package()
    make_symlink()



@hosts('localhost')
@task
def update_db():

    conn = sqlite3.connect('/var/lib/jenkins/scripts/update.db')
    cursor = conn.cursor()
    cursor.execute("select version from %s where version=\'%s\'" % (env.deploy_name,env.deploy_version))
    values = cursor.fetchall()
    if len(values) == 0:
        cursor.execute("insert into %s (version) values (\'%s\')" %(env.deploy_name,env.deploy_version))
    else:
        print "Insert failed!Already has %s" %(env.deploy_version)
    cursor.close()
    conn.commit() 
    conn.close()
