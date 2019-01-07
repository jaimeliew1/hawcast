#!/usr/bin/env python
import argparse
import sys
import os
from hawcast import backend

def htc(definition, dest=None, master_fn=None):
    if master_fn == None:
        master_fn = os.path.join('htc/_master',
        os.path.splitext(os.path.basename(definition))[0] + '.htc')
    case = backend.Case(definition)
    print('Creating {} htc files...'.format(len(case.tags)))
    backend.generate_htc_files(case.tags, master_fn)


def jess(htc_dir, dest=None):
    pbs_template = os.path.join(os.path.dirname(__file__), 'pbs_template.p')

    htc_files = [x for x in os.listdir(htc_dir) if x.endswith('.htc')]
    print('Creating {} .p files...'.format(len(htc_files)))
    for file in htc_files:
        backend.htc2pbs(os.path.join(htc_dir, file), pbs_template)



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
        htc(args.definition, master_fn=args.master)




    def jess(self):
        parser = argparse.ArgumentParser(
            description='Generates launch scripts for jess HPC')
        # NOT prefixing the argument with -- means it's not optional
        #parser.add_argument('repository')
        parser.add_argument('htc_dir', help='Relative filepath to htc folder')
        args = parser.parse_args(sys.argv[2:])
        print('Running hawcast.py jess...')
        jess(args.htc_dir)



    def launch(self):
        pass



    def postproc(self):
        pass

def main():
    print()
    Hawcast_parser()


if __name__ == '__main__':
    main()
