import os, sys, zipfile, importlib
import numpy as np
import pandas as pd
import re as magic
from itertools import product

from wetb.hawc2.htc_file import HTCFile
from wetb.fatigue_tools.fatigue import eq_load

from .myDataFrame import myDataFrame



def import_path(fullpath):
    """ Import a python script as a module from an arbitrary filepath
    """
    path, filename = os.path.split(fullpath)
    filename, ext  = os.path.splitext(filename)
    sys.path.append(path)
    module = importlib.import_module(filename)
    del sys.path[-1]
    return module



def htc2bat(htc_dir, n=1, filter='all', app='hawc2mb'):

    htc_files = [os.path.join(htc_dir, x) for x in os.listdir(htc_dir) if x.endswith('.htc')]
    bat_dir = 'bat'
    if not os.path.exists(bat_dir):
        os.makedirs(bat_dir)

    chunks = chunkify(htc_files, n)

    for i, chunk in enumerate(chunks):
        with open(os.path.join(bat_dir, f'{i+1}.bat'), 'w') as f:
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

    #read .sel file
    with open(filename + '.sel') as f:
        lines = f.readlines()

    NCh             = int(lines[8].split()[1])
    NSc             = int(lines[8].split()[0])
    Format          = lines[8].split()[3]
    scaleFactor     = [float(x) for x in lines[NCh+14:]]

    if channels is None:
        channels = {str(i):i for i in range(NCh)}

    #read .bin file
    data = {}
    fid = open(filename + '.dat', 'rb')
    for key, ch in channels.items():
        fid.seek((ch-1)*NSc*2)
        data[key] = np.fromfile(fid, 'int16', NSc) * scaleFactor[ch-1]

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


    def loadData(self):
        try:
            data = readHawc2Res(self.res[:-4], self.definition.channels)
        except:
            print('error loading data ' + self.tags.case_id)
            data = None

        return data


    def __repr__(self):
        return('Seed {}'.format(self.tags.case_id))



class Case(object):
    # a base class that holds the simulation definitions
    def __init__(self, definition):

        #self.Definition = self.add_definition(definition)
        self.Def = import_path(definition)
        self.tags = self.gen_tags(self.Def.Constants, self.Def.Variables, self.Def.Functions)

        self.seeds = []
        for _, row in self.Def.tags.iterrows():
            self.seeds.append(Seed(self.Def, row))

    def __repr__(self):
        return self.tags.__repr__()

    def __iter__(self):
            yield from self.seeds

    def __call__(self, **kwargs):
        mask = self.tags(**kwargs)
        return [i for (i, v) in zip(self.seeds, mask) if v]



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
