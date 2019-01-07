import numpy as np
import pandas as pd
import os, sys
import importlib
import re as magic
from itertools import product
from wetb.hawc2.htc_file import HTCFile
from wetb.fatigue_tools.fatigue import eq_load
import zipfile


def import_path(fullpath):
    """ Import a file from an arbitrary filepath
    """
    path, filename = os.path.split(fullpath)
    filename, ext  = os.path.splitext(filename)
    sys.path.append(path)
    module = importlib.import_module(filename)
    del sys.path[-1]
    return module



def check_definition(definition_fn, master_fn):
    imported = import_path(definition_fn)

    with open(master_fn) as f:
        template = f.read()

    template_keys = set(magic.findall('\{(.*?)\}', template))
    definition_keys =   list(imported.Constants.keys()) + \
                        list(imported.Variables.keys()) + \
                        list(imported.Functions.keys())

    print('in definition but not in template:')
    for key in template_keys:
        if key not in definition_keys: print(key)
    print('in template but not in definition:')
    for key in definition_keys:
        if key not in template_keys: print(key)



def makeBat(case, N=1, filter='all', bit64=False):

    if filter == 'all':
        toRun = []
    for tags in case.iter_tags():
        toRun.append('htc\\' + tags.casename + '\\' + tags.case_id + '.htc')


    bat_dir = 'bat\\'
    if not os.path.exists(bat_dir):
        os.makedirs(bat_dir)
    chunks = chunkify(toRun, N)

    if bit64:
        app = 'hawc2mb_64'
    else:
        app = 'hawc2mb'
    for i, chunk in enumerate(chunks):
        with open(bat_dir + '{}.bat'.format(i), 'w') as f:
            f.write('cd ..\n')
            for file in chunk:
                f.write(f'{app} {file}\n')


def chunkify(lst, n):
# splits a list into n groups of approximately the same length
    return [lst[i::n] for i in range(n)]


def generate_htc_files(tag_list, template_fn, overwrite=True):
    # generates htc files using a template htc file located at template_fn.
    # uses parameters from self.params. if no destination folder is provided,
    # the files are written in self.HTCDir. If overwrite is False, only
    # htc files which do not exist will be written. Otherwise, all files will
    # be written.


    # error check
    if not os.path.isfile(template_fn):
        raise FileNotFoundError('Template file {} does not exist.'.format(template_fn))


    with open(template_fn) as f:
        TemplateText = f.read()

    for _, paramset in tag_list.iterrows():
        dest = 'htc/' + paramset.casename + '/'
        if not os.path.exists(dest):
            os.makedirs(dest)

        if not overwrite:
            if os.path.exists(dest + paramset.case_id + '.htc'):
                continue

        FileText = TemplateText
        for key, value in paramset.items():
            FileText = FileText.replace('{' + key + '}', str(value))

        with open(dest + paramset.case_id + '.htc', 'w') as f:
            f.write(FileText)



def readHawc2Res(filename, channels=None):
    #reads specific channels of HAWC2 binary output files and saves in a
    #pandas dataframe. Variable names and channels are defined in a dictionary
    # called channels

    if channels is None:
        raise NotImplementedError()


    #read .sel file
    with open(filename + '.sel') as f:
        lines = f.readlines()

    NCh             = int(lines[8].split()[1])
    NSc             = int(lines[8].split()[0])
    Format          = lines[8].split()[3]
    scaleFactor     = [float(x) for x in lines[NCh+14:]]

    #read .bin file
    data = {}
    fid = open(filename + '.dat', 'rb')
    for key,ch in channels.items():
        fid.seek((ch-1)*NSc*2)
        data[key] = np.fromfile(fid,'int16',NSc) * scaleFactor[ch-1]

    out = pd.DataFrame(data)
    return out






class Seed(object):
    # the seed class should keep track of the htc file and result file of a
    # single simulation.
    def __init__(self, definition, row):
        self.tags = row
        self.definition = definition
        self.htc = 'htc/' + self.tags.casename + '/' + self.tags.case_id + '.htc'
        self.log = None
        self.res  = 'res/' + self.tags.casename + '/' + self.tags.case_id + '.sel'
        self.postproc = 'postproc/' + self.tags.casename + '/' + self.tags.case_id

        #self.parent = parent
        #self.filepath = filepath # filepath to the result file. !!! what about htc file?
        #self.att = row


        for att in self.definition.key_tags:#self.parent.input_attributes:
            setattr(self, att, row[att])

    def loadData(self):
        try:
            data = readHawc2Res(self.res[:-4], self.definition.channels)
        except:
            print('error loading data ' + self.tags.case_id)
            data = None

        return data

    def status(self):
        if os.path.getmtime(self.definition.filepath) > os.path.getmtime(self.htc):
            return 'htc unsyncronised'
        if os.path.getmtime(self.definition.filepath) > os.path.getmtime(self.res):
            return 'results unsyncronised'
        else:
            return 'Syncronised'

    def __repr__(self):
        return('Seed {}'.format(self.tags.case_id))

    def __eq__(self, other):
        return False


    def analysis(self):
        pass





class Case(object):
    # a base class that holds the simulation definitions
    def __init__(self, definition):

        self.Definition = self.add_definition(definition)
        self.tags = self.Definition.tags

        self.seeds = []
        for _, row in self.Definition.tags.iterrows():
            self.seeds.append(Seed(self.Definition, row))
#        for _, row in self.tags.iterrows():
#            filename = 'res/' + row.casename + '/' + row.case_id
#            self.seeds.append(Seed(self, filename, row))
#

    def __repr__(self):
        return self.tags.__repr__()

    def __iter__(self):
            yield from self.seeds

    def __call__(self, **kwargs):
        mask = self.mask(**kwargs)
        return [i for (i, v) in zip(self.seeds, mask) if v]

#

    def add_definition(self, filename):
        # assert filename.lower().endswith('.py')
        def_mod = import_path(filename)
        def_mod.tags = self.gen_tags(def_mod.Constants, def_mod.Variables, def_mod.Functions)
        def_mod.filepath = filename

        if hasattr(def_mod, 'masterfile'):
            pass
        if hasattr(def_mod, 'key_tags'): # TODO get rid of this
            self.input_attributes = def_mod.key_tags
        return def_mod


    def iter_tags(self, **kwargs):
        for _, tags in self.tags(**kwargs).iterrows():
            yield tags



    def iter_results(self, **kwargs):
        for sim in self(**kwargs):
            try:
                res = sim.loadData()
            except:
                res = None
            yield sim.tags, res



    def gen_tags(self, Consts, Vars, Funcs):

    # number of combinations:
        self.N = 1
        for n in [len(x) for x in Vars.values()]:
            self.N *= n
    # number of attributes:
        attributes = list(Consts.keys()) + list(Vars.keys()) + list(Funcs.keys())
        self.M = len(attributes)

    # generate a Pandas dataframe where each row has one of the combinations
    # of simulation tags
        manifest = []
        for v in product(*list(Vars.values())):
            v_dict = dict(zip(Vars.keys(), v))
            this_dict = {**Consts, **v_dict}

            for key, f in Funcs.items():

                this_dict[key] = f(this_dict)

            manifest.append(list(this_dict.values()))

        return myDataFrame(manifest, columns=attributes)




    def crawl(self, crawlfunc, **kwargs):
        # TODO: think about how to make this cleaner
        big_dict = {}
        for att, data in self.iter_results(**kwargs):
            if data is None:
                continue
            this_dict = att.to_dict()
            out_dict = crawlfunc(data)
            this_dict.update(out_dict)

            # !!! This loop could case issues. Assumes keys in att, out_dict are
            # always the same.
            for key, val in this_dict.items():
                if key not in big_dict.keys():
                    big_dict[key] = []
                big_dict[key].append(val)

        return myDataFrame(big_dict)



    def _mask(self, df, **kwargs):

        '''
        Returns a mask for refering to a dataframe, or self.Data, or self.Data_f, etc.
        example. dlc.mask(wsp=[12, 14], controller='noIPC')
        '''
        N = len(df)
        mask = [True] * N
        for key, value in kwargs.items():
            if isinstance(value, (list, tuple, np.ndarray)):
                mask_temp = [False] * N
                for v in value:
                    mask_temp = mask_temp | (df[key] == v)
                mask = mask & mask_temp
            else: #scalar, or single value
                mask = mask & (df[key] == value)
        return mask

    def mask(self, **kwargs):
        return self._mask(self.tags, **kwargs)


class Generator(Case):
    pass

class Reader(Case):
    pass


class myDataFrame(pd.DataFrame):
    ''' A modified pandas dataframe that can be called. The call function filters and
    returns the rows which meet the conditions set by the keyword arguments in
    the call.'''

    @property
    def _constructor(self):
        return myDataFrame


    def __call__(self, **kwargs):
        return self[self._mask( **kwargs)]


    def _mask(self, **kwargs):
        '''
        Returns a mask for refering to a dataframe, or self.Data, or self.Data_f, etc.
        example. dlc.mask(wsp=[12, 14], controller='noIPC')
        '''
        N = len(self)
        mask = [True] * N
        for key, value in kwargs.items():
            if isinstance(value, (list, tuple, np.ndarray)):
                mask_temp = [False] * N
                for v in value:
                    mask_temp = mask_temp | (self[key] == v)
                mask = mask & mask_temp
            else: #scalar, or single value
                mask = mask & (self[key] == value)
        return mask



def generate_model_zip(zipfilename):
    zipf = zipfile.ZipFile(zipfilename, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk('control'):
        for file in files:
            zipf.write(os.path.join(root, file))

    for root, dirs, files in os.walk('data'):
        for file in files:
            zipf.write(os.path.join(root, file))
    zipf.close()


def htc2pbs(htc_fn, pbs_template_fn):
    """
    Creates a PBS launch file (.p) based on a HAWC2 .htc file.
    - Assumes htc files are within a htc/[casename]/ directory relative to current directory.
    - Assumes there is a .zip file in the current directory which contains the turbine model.
      If there is none, the zip file is set to 'model.zip' by default
    - Will place a .p fine in pbs_in/[casename]/ directory relative to current directory.
    -

    Parameters
    ----------
    htc_fn : str
        The file name and path to the .htc file
    pbs_template_fn : str
        The filename and path to the template .p file


    Returns
    -------
    str
        The filename and path to the output .p file

    Raises
    ------
    FileNotFoundError: If the file structure is not correct.
    """



    basename = os.path.relpath(os.path.dirname(htc_fn), 'htc')
    jobname = os.path.splitext(os.path.basename(htc_fn))[0]
    pbs_in_dir = os.path.join('pbs_in', basename)
    if basename == '.':
        raise FileNotFoundError('File structure is incorrect.')


    try:
        zipfile = [x for x in os.listdir() if x.lower().endswith('.zip')][0]
    except:
        print('No .zip file found in current directory. Set model zip to \'model.zip\'')
        zipfile = 'model.zip'

    #   get the required parameters for the pbs file from the htc file
    htc = HTCFile(htc_fn) #modelpath='../..')
    p = {
        'walltime'      : '00:40:00',
        'modelzip'      : zipfile,
        'jobname'       : jobname,
        'htcdir'        : 'htc/' + basename,
        'logdir'        :  os.path.dirname(htc.simulation.logfile.str_values())[2:] + '/',
        'resdir'        : os.path.dirname(htc.output.filename.str_values())[2:] + '/',
        'turbdir'       : os.path.dirname(htc.wind.mann.filename_u.str_values()) + '/',
        'turbfileroot'  : os.path.basename(htc.wind.mann.filename_u.str_values()).split('u.')[0],
        'pbsoutdir'     : 'pbs_out/' + basename
        }


    #Write pbs file based on template file and tags
    if not os.path.exists(pbs_in_dir):
        os.makedirs(pbs_in_dir)

    with open(pbs_template_fn) as f:
        template = f.read()

    for key, value in p.items():
        template = template.replace('[' + key + ']', value)

    with open(os.path.join(pbs_in_dir, jobname + '.p'), 'w') as f:
        f.write(template)
        #print('{}.p created.'.format(jobname))
