import pandas as pd

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
