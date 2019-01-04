#!/usr/bin/env python
import argparse
import sys

def htc(definition, dest=None, master=None):
    pass


def jess(htc_dir, dest=None):
    pass


def postproc(res_dir):
    pass


class Hawcast_parser(object):

    def __init__(self):
        parser = argparse.ArgumentParser(
            description =
            '''Hawcast - a HAWC2 workflow tool based on WETB ''',
            usage       ='hawcast.py <command> [<args>]')


        parser.add_argument('command', help='Subcommand to run')
        # parse_args defaults to [1:] for args, but we need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()




    def htc(self):
        parser = argparse.ArgumentParser(
            description='Generate HTC files',
            usage='''hawcast.py htc <definition> [--master]''')
        # prefixing the argument with -- means it's optional
        parser.add_argument('definition', help='Relative filepath to htc definition file.')
        parser.add_argument('--master', help='Relative filepath to master HTC file.')
        # now that we're inside a subcommand, ignore the first
        # TWO argvs, ie the command (hawcast.pu) and the subcommand (htc)
        args = parser.parse_args(sys.argv[2:])
        print('Running hawcast.py htc...')




    def jess(self):
        parser = argparse.ArgumentParser(
            description='Generates launch scripts for jess HPC')
        # NOT prefixing the argument with -- means it's not optional
        #parser.add_argument('repository')
        args = parser.parse_args(sys.argv[2:])
        print('Running hawcast.py jess...')



    def launch(self):
        pass



    def postproc(self):
        pass
if __name__ == '__main__':
    Hawcast_parser()
