#!/usr/bin/env python
import argparse
import sys
import os
from hawcast import backend
import click


@click.group()
def cli():
    '''Hawcast - a HAWC2 workflow tool based on WETB '''
    pass


@cli.command()
@click.argument('definition')
@click.argument('dest', required=False)
@click.option('--master', help='Relative filepath to master HTC file.')
def htc(definition, dest=None, master=None):
    ''' Generate htc files'''
    if master == None:
        master = os.path.join('htc/_master',
        os.path.splitext(os.path.basename(definition))[0] + '.htc')
    case = backend.Case(definition)
    print('Creating {} htc files...'.format(len(case.tags)))
    backend.generate_htc_files(case.tags, master)



@cli.command()
@click.argument('htc_dir')
@click.argument('dest', required=False)
def jess(htc_dir, dest=None):
    '''Generates launch scripts for jess HPC'''
    pbs_template = os.path.join(os.path.dirname(__file__), 'pbs_template.p')

    htc_files = [x for x in os.listdir(htc_dir) if x.endswith('.htc')]
    print('Creating {} .p files...'.format(len(htc_files)))
    for file in htc_files:
        backend.htc2pbs(os.path.join(htc_dir, file), pbs_template)



@cli.command()
@click.argument('htc_dir')
@click.argument('dest', required=False)
@click.option('-n', default=1)
def bat(htc_dir, dest=None, n=1):
    '''Generates bat launch files from htc files.'''
    n_htc = len([x for x in os.listdir(htc_dir) if x.endswith('.htc')])
    print(f'Creating {n} bat files for {n_htc} htc files...')
    backend.htc2bat(htc_dir, n)
