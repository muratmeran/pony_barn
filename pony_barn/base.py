import sys
import os
import tempfile
import shutil
import optparse

import pony_barn.client as pony

class BaseBuild(object):
    def __init__(self):
        self.required = []

    def setup(self):
        "This is where subclasses define extra setup."
        pass

    def define_commands(self):
        "This is where subclasses define how they are run."
        pass

    def execute(self, argv):
        self.add_options()
        self.options, self.args = self.cmdline.parse_args(argv)

        if not self.options.server_url:
            self.server_url = 'http://devmason.com/pony_server/xmlrpc'
        else:
            self.server_url = self.options.server_url

        self.get_tags()
        self.check_build()
        self.context = pony.VirtualenvContext(always_cleanup=self.options.cleanup_temp,
                                              use_site_packages=self.options.site_packages,
                                              dependencies=self.required)
        self.setup()
        self.define_commands()
        results = pony.do(self.name, self.commands, context=self.context)
        return self.report(results)


    def add_options(self):
        self.cmdline = optparse.OptionParser()
        self.cmdline.add_option('-f', '--force-build', dest='force_build',
                           action='store_true', default=False,
                           help="run a build whether or not it's stale")
        self.cmdline.add_option('-r', '--report', dest='report',
                           action='store_true', default=False,
                           help="report build results to server")
        self.cmdline.add_option('-N', '--no-clean-temp', dest='cleanup_temp',
                           action='store_false', default=True,
                           help='do not clean up the temp directory')
        self.cmdline.add_option('-s', '--server-url', dest='server_url',
                           action='store', default='',
                           help='set pony-build server URL for reporting results')
        self.cmdline.add_option('-v', '--verbose', dest='verbose',
                           action='store_true', default=False,
                           help='set verbose reporting')
        self.cmdline.add_option('-P', '--site-packages', dest='site_packages',
                           action='store_true', default=False,
                           help='Use the system site packages')

    def get_tags(self):
        # Figure out the python version and tags
        py_version = ".".join(str(p) for p in sys.version_info[:2])
        self.py_name = 'python%s' % py_version
        self.tags = [self.py_name, 'base_builder']

    def check_build(self):
        if not self.options.force_build:
            if not pony.check(self.name, self.server_url, tags=self.tags):
                print 'check build says no need to build; bye'
                sys.exit(0)

    def report(self, results):
        client_info, reslist = results
        if self.options.report:
            print 'Result: %s; sending' % (client_info['success'],)
            pony.send(self.server_url, results, tags=self.tags)
        else:
            print
            print "-"*60
            print 'Build results:'
            print '(not sending build results to server)'
            print
            print "Client info:"
            for (k, v) in client_info.items():
                print "  %s: %s" % (k, v)
            print
            print "Build details:"
            for i, step in enumerate(reslist):
                print "  Step %s: %s" % (i, step['name'])
                for k, v in step.items():
                    print "    %s: %s" % (k, v)

        if not client_info['success']:
            return -1
        return 0