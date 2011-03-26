import os
from distutils.cmd import Command
from distutils import log

from nbdebug import *

def run(command) :
  debugOutput(command)
  os.system(command)

class DebianPackager :

  def __init__(self, distribution) :
    debugOutput("Creating")
    self.distribution = distribution

    name = self.distribution.metadata.name
    version = self.distribution.get_version()
    self.name_version = "%s_%s_all" % (name, version)
    
    # Setup paths.
    self.codeRoot = os.path.dirname(os.path.abspath(self.distribution.script_name))
    self.sourceDistFile = os.path.join(self.codeRoot, "dist", "%s-%s.tar.gz" % (name, version))
    self.packageDir = os.path.join(self.codeRoot, "dist", self.name_version)


  def getDepends(self) :
    return open(os.path.join(self.codeRoot, "sys-deps"),"r").read().strip()

  def getPostinst(self) :
    template = """#!/bin/sh
cd /tmp
tar -xzf DIR.tar.gz
cd DIR
ls
rm -fr DIR
python setup.py install
""" 
    
    content = template.replace("DIR", os.path.basename(self.sourceDistFile).replace(".tar.gz",""))
    debugOutput(content)
    return content

  def getPrerm(self) :
    # TODO: update this
    template = """#!/bin/sh
easy_install -m APP_NAME
find /usr/lib -name 'APP_NAME*' -print | xargs /bin/rm -rf
rm /usr/bin/wikidbase-admin
rm -fr /usr/lib/wikidbase 
""" 
    
    content = template.replace("APP_NAME", self.distribution.metadata.name)
    debugOutput(content)
    return content


  def controlFile(self) :
    # Creates control file contents.

    control = [
      ("Package", self.distribution.metadata.name),
      ("Version", self.distribution.get_version()),
      ("Section", "python"),
      ("Priority", "optional"),
      ("Architecture", "all"),
      ("Depends", self.getDepends()),
      ("Maintainer", self.distribution.metadata.author),
      ("Homepage","http://projects.nickblundell.org.uk"),
      #("",""),
      ("Description", self.distribution.metadata.long_description),
    ]

    contents = ""
    for item in control :
      contents += ": ".join(item) + "\n"

    debugOutput(contents)

    return contents

  def createPackage(self) :
    debugOutput("Creating")
 
    assert(os.path.exists(self.sourceDistFile))

    # make deb dir with same name as app
    run("mkdir -p '%s'" % self.packageDir)

    if os.path.exists(self.packageDir) :
      run("rm -fr '%s'" % self.packageDir)
    
    # Create config files
    configDir = os.path.join(self.packageDir, "DEBIAN")
    run("mkdir -p '%s'" % configDir)
    open(os.path.join(configDir,"control"), "w").write(self.controlFile())
   
    # Copy postinst, prerm
    postinst = os.path.join(configDir, "postinst")
    prerm = os.path.join(configDir, "prerm")
    open(postinst,"w").write(self.getPostinst())
    open(prerm,"w").write(self.getPrerm())
    run("chmod +x '%s'" % postinst)
    run("chmod +x '%s'" % prerm)

    # Copy data file
    run("mkdir -p '%s'" % os.path.join(self.packageDir, "tmp"))
    run("cp '%s' '%s'" % (self.sourceDistFile, os.path.join(self.packageDir, "tmp")))
    
    # package for deb
    debFile = self.packageDir + ".deb"
    run("dpkg --build '%s' '%s'" % (self.packageDir, debFile))
    
    # Remove temp files.
    #os.remove("rm -fr '%s'" % self.packageDir)

class bdist_deb(Command):
    """bdist_deb"""

    description = "Create a deb package"
    user_options = [ ]

    def initialize_options (self):
        pass

    def finalize_options (self):
        bdist_base = self.get_finalized_command('bdist').bdist_base
        self.bdist_dir = os.path.join(bdist_base, 'deb')
        self.dist_dir = self.get_finalized_command('bdist').dist_dir

    def run (self):
       
        # Make the source distribution, which will go into the debian package.
        self.run_command('sdist')

        debianPackager = DebianPackager(self.distribution)
        debianPackager.createPackage()

PRERM = """
"""
