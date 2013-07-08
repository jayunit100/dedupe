
class FnameMap(object):
    """
    Question:  is it right or wrong that giving it the same text twice
    returns a different id?
    """

    def __init__(self):
        self.map2val = [] #maps id to file name
    
    def get_id(self, text) :
        """Maps file names to unique file numbers and maintains mapping tables"""
        idx = len(self.map2val)
        self.map2val.append(text)
        return idx
    
    def get_name(self, idx) :
        return self.map2val[idx]


class ChecksumMap:    
    """
    Class for mapping checksum values to numeric key, and maintaining counts
    """
    
    def __init__(self):
        self.map2idx = {}
        self.map2hval = []
        self.counts = []

    def get_id(self, hval):
        """Maps hashes to unique hash numbers and maintains mapping tables"""
        fingerprint = hval['c'] + hval['r'] #include range in checksum name
        if fingerprint in self.map2idx:
            idx = self.map2idx[fingerprint]
            self.counts[idx] += 1
            return idx
        else:
            idx = len(self.map2hval)
            self.map2idx[fingerprint] = idx
            self.map2hval.append(hval)
            self.counts.append(1)
            return idx
        
    def get_hval(self, idx):
        return self.map2hval[idx]

    def get_count(self, idx):
        return self.counts[idx]
