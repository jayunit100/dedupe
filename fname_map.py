import string



#---------------------------------------------------
# Tables for mapping fname and hash values to numeric keys
#---------------------------------------------------


class FnameMap(object):
    """
    Class for mapping file names to numeric key
    >>> FnameMap.reset()
    >>> FnameMap.get_id('aaa')
    0
    >>> FnameMap.get_id('bbb')
    1
    >>> FnameMap.get_id('ccc')
    2
    >>> FnameMap.get_name(0)
    'aaa'
    >>> FnameMap.get_name(1)
    'bbb'
    >>> FnameMap.get_name(2)
    'ccc'
    >>> FnameMap.get_name_using_encoded_id('F:2')
    'ccc'
    >>> FnameMap.reset()
    >>> FnameMap.get_id('ddd')
    0
    >>> FnameMap.get_name(0)
    'ddd'
    >>> FnameMap.reset()
    """

    map2val = []  #maps id to file name
    
    @classmethod
    def get_id(cls, text) :
        """Maps file names to unique file numbers and maintains mapping tables"""
        idx = len(cls.map2val)
        cls.map2val.append(text)
        return idx
    
    @classmethod
    def get_name(cls, idx) :
        return cls.map2val[idx]

    @classmethod
    def get_name_using_encoded_id(cls, eidx):
        return cls.map2val[cls.decode(eidx)]
    
    @classmethod
    def reset(cls):
        cls.map2val = []

    @staticmethod
    def encode(idx):
        """
        adds type prefix to fno -- ensures uniqueness since fno
        and hno share same node namespace
        >>> FnameMap.encode(1)
        'F:1'
        """
        return 'F:{}'.format(idx)

    @staticmethod
    def decode(text):
        """
        strip off prefix and return numeric value
        >>> FnameMap.decode('F:1')
        1
        """
        (node_type, idx) = string.rsplit(text, ':', 1)
        return int(idx)



class ChecksumMap:    
    """
    Class for mapping checksum values to numeric key, and maintaining counts
    >>> ChecksumMap.reset()
    >>> ChecksumMap.get_id({'c':'aaa', 'r':'x'})
    0
    >>> ChecksumMap.get_id({'c':'bbb', 'r':'y'})
    1
    >>> ChecksumMap.get_id({'c':'ccc', 'r':'z'})
    2
    >>> ChecksumMap.get_id({'c':'bbb', 'r':'y'})
    1
    >>> ChecksumMap.get_id({'c':'ccc', 'r':'z'})
    2
    >>> ChecksumMap.get_id({'c':'bbb', 'r':'y'})
    1
    >>> ChecksumMap.get_hval(0)
    {'c': 'aaa', 'r': 'x'}
    >>> ChecksumMap.get_hval(1)
    {'c': 'bbb', 'r': 'y'}
    >>> ChecksumMap.get_hval(2)
    {'c': 'ccc', 'r': 'z'}
    >>> ChecksumMap.get_count(0)
    1
    >>> ChecksumMap.get_count(1)
    3
    >>> ChecksumMap.get_count(2)
    2
    >>> ChecksumMap.reset()
    >>> ChecksumMap.get_id({'c':'ddd', 'r':'q'})
    0
    >>> ChecksumMap.get_hval(0)
    {'c': 'ddd', 'r': 'q'}
    >>> ChecksumMap.get_count(0)
    1
    >>> ChecksumMap.get_encoded_id({'c':'eee', 'r':'r'})
    'H:1'
    >>> ChecksumMap.get_hval_using_encoded_id('H:1')
    {'c': 'eee', 'r': 'r'}
    >>> ChecksumMap.get_range_using_encoded_id('H:1')
    'r'
    >>> ChecksumMap.reset()
    """

    map2idx = {}
    map2hval = []
    counts = []

    @classmethod
    def get_id(cls, hval) :
        """Maps hashes to unique hash numbers and maintains mapping tables"""
        fingerprint = hval['c']+hval['r'] #include range in checksum name
        if fingerprint in cls.map2idx:
            idx = cls.map2idx[fingerprint]
            cls.counts[idx] += 1
            return idx
        else :
            idx = len(cls.map2hval)
            cls.map2idx[fingerprint] = idx
            cls.map2hval.append(hval)
            cls.counts.append(1)
            return idx
        
    @classmethod
    def get_encoded_id(cls, hval):
        return cls.encode(cls.get_id(hval))
        
    @classmethod
    def get_hval(cls, idx) :
        return cls.map2hval[idx]

    @classmethod
    def get_hval_using_encoded_id(cls, eidx):
        return cls.map2hval[cls.decode(eidx)]
        
    @classmethod
    def get_range_using_encoded_id(cls, eidx):
        return cls.map2hval[cls.decode(eidx)]['r']
    
    @classmethod
    def get_count(cls,idx) :
        return cls.counts[idx]
    
    @classmethod
    def reset(cls):
        cls.map2idx = {}
        cls.map2hval = []
        cls.counts = []

    @staticmethod
    def encode(idx):
        """
        adds type prefix to hno -- ensures uniqueness since fno
        and hno share same node namespace
        >>> ChecksumMap.encode(1)
        'H:1'
        """
        return 'H:{}'.format(idx)

    @staticmethod
    def decode(text):
        """
        strip off prefix and return numeric value
        >>> ChecksumMap.decode('H:1')
        1
        """
        (node_type, idx) = string.rsplit(text, ':', 1)
        return int(idx)
 

if __name__ == "__main__":
    import doctest
    doctest.testmod()
