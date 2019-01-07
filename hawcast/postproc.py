## -*- coding: utf-8 -*-
"""
Created on 2019-01-07

@author: jyli
"""

import re, os, sys
import numpy as np
import pandas as pd
from .backend import readHawc2Res, myDataFrame
from wetb.fatigue_tools.fatigue import eq_load


class HAWC2Res(object):
    """A class that processes HAWC2 result files. The result files
       should be contained in a directory and be named by a common string
       pattern"""
    pattern_string = None
    channels       = None

    @property
    def _constructor(self):
       return HAWC2Res

    def __init__(self, directory, pattern_string=None, channels=None):
        # !!!  I dont know how to do the constructor
        self.directory = directory
        pattern_string = pattern_string or self.pattern_string
        pattern, self.fields = self._compile_pattern(pattern_string)

        # get all filenames that fit the pattern
        self.filenames = [x[:-4] for x in os.listdir(directory) if x.endswith('.sel')]
        self.filenames = [x for x in self.filenames if pattern.match(x)]

        self.channels = channels or self.channels
        # Extract input attributes and put in dataframe
        self.dat = []
        for fn in self.filenames:
            self.dat.append([float(x) for x in pattern.findall(fn)[0]])
        self.dat = myDataFrame(self.dat)

        # set column multi index
        column_tuples = list(zip(*[self.fields, ['']*len(self.fields)]))
        self.dat.columns = pd.MultiIndex.from_tuples(column_tuples,
            names=['channel', 'stat'])

        self.run()


    def run(self):
        # Run in initialisation. To be overwritten when class is inherited
        pass


    def __repr__(self):
        return self.dat.__repr__()


    @staticmethod
    def _compile_pattern(pattern_string):
        brackets = re.compile('{(.*?)}')
        fields = brackets.findall(pattern_string)
        for field in fields:
            pattern_string = pattern_string.replace('{'+ field +'}', '(.*)')
        return re.compile(pattern_string), fields


    def add_mean(self, channels=None):
        print('Calculating mean...')
        mean = []
        if channels is None:
            channels = self.channels
        else:
            channels = {k:v for k,v in self.channels.items() if k in channels}
        N = len(self.filenames)
        for i, fn in enumerate(self.filenames):
            print(f'\r{i+1}/{N}', end='')
            mean.append(readHawc2Res(os.path.join(self.directory, fn), channels).mean().values)
        print()
        df = pd.DataFrame(mean)
        # add multi index columns
        col_ch     = list(channels.keys())
        col_stat   = ['mean']*len(col_ch)
        col_tuples = list(zip(*[col_ch, col_stat]))
        df.columns = pd.MultiIndex.from_tuples(col_tuples,
                    names=['channel', 'stat'])

        self.dat = self.dat.join(df)
        return self

    def add_DEL(self, channels, m=4):
        print(f'Calculating 1 Hz DEL for m={m}...')
        print(', '.join(ch for ch in channels))
        DEL = []
        if channels is None:
            channels = self.channels
        else:
            channels = {k:v for k,v in self.channels.items() if k in channels}
        N = len(self.filenames)
        for i, fn in enumerate(self.filenames):
            print(f'\r{i+1}/{N}', end='')
            raw = readHawc2Res(os.path.join(self.directory, fn), channels)
            DEL.append([])
            for k in channels.keys():
                DEL[-1].append(eq_load(raw[k].values, m=m)[0][0])
        print()
        df = pd.DataFrame(DEL)
        # add multi index columns
        col_ch     = list(channels.keys())
        col_stat   = ['DEL']*len(col_ch)
        col_tuples = list(zip(*[col_ch, col_stat]))
        df.columns = pd.MultiIndex.from_tuples(col_tuples,
                    names=['channel', 'stat'])

        self.dat = self.dat.join(df)
        return self

    def mean_over_row(self, key):
        # used for taking the mean over all seeds
        print(f'Calculating mean over key={key}...')
        in_fields = [x for x in self.fields if x != key]
        out_fields = [x for x in list(self.dat) if x[0] not in self.fields]
        in_atts = self.dat[in_fields].drop_duplicates()
        new_dat = []
        N = len(in_atts)
        for i, (_, x) in enumerate(in_atts.iterrows()):
            print(f'\r{i+1}/{N}', end='')
            filt = {k[0]: v for k, v in dict(x).items()}
            new_dat.append(list(x) + list(self.dat(**filt)[out_fields].mean().values))
        print()
        self.dat = myDataFrame(new_dat)
        # add multi index columns
        col_ch     = in_fields + [x[0] for x in out_fields]
        col_stat   = ['']*len(in_fields) + [x[1] for x in out_fields]
        col_tuples = list(zip(*[col_ch, col_stat]))
        self.dat.columns = pd.MultiIndex.from_tuples(col_tuples,
                    names=['channel', 'stat'])
        return self

    def mean_over_col(self, key_root):
        # used for taking the mean over all blades.
        print(f'Calculating mean over key={key_root}...')
        # get all unique stat indices
        col_stat = list(set(x[1] for x in list(self.dat)))
        for stat in col_stat:
            keys = [x for x in list(self.dat) if key_root in x[0] and x[1] == stat]
            if not keys:
                continue
            self.dat[(key_root, stat)] = self.dat[keys].mean(axis=1)
        return self

    def sort_columns(self):
        # sorts the columns so that input attributes are first, then output
        # attributes grouped by channel. # TODO
        # use this function to sort by channel in multiindexed columns
        #self.dat.sort_index(axis='columns', level='channel', inplace=True)
        pass

    def to_csv(self, fn):
        print(f'Saving data to {fn}...')
        self.dat.to_csv(fn, index=False)



if __name__ == '__main__':
    pass
