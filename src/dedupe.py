import re
from .fname_map import FnameMap, ChecksumMap


#--------------------------------------
# File level deduplication
#--------------------------------------

#parse entry in format hash filename
md5deep_file_re = re.compile("([0-9abcdef]+)\s+(\S.+)$")

def parse_md5deep_file_entry(text) :
    """parses individual lines from md5deep"""
    try:
        parse = md5deep_file_re.search(text)
        g1, g2 = parse.groups()  # <-- can raise exception if regex doesn't match
        return (g1, g2)
    except:
        raise ValueError('md5deep lines not found: ' + text)

def identify_duplicates(lines):
    """groups line names by line values.
    doesn't assume anything about input order
    actually shouldn't be responsible for using the parse function"""
    duplicates = {}
    for line in lines:
        (key, name) = parse_md5deep_file_entry(line)
        if not duplicates.has_key(key):
            duplicates[key] = []
        duplicates[key].append(name)
    return duplicates


def create_duplicate_map(duplicates):
    """creates a duplicate map, indexed by first duplicate file"""
    dup_map = {}
    for dup_group in duplicates.values():
        primary = dup_group[0]
        for secondary in dup_group[1:]:
            dup_map[secondary] = primary
    return dup_map


def find_duplicateFiles(lines):
    """find all duplicate files based on MD5 hashes"""
    duplicates = identify_duplicates(lines)
    return duplicates
   
    
#----------------------------------------------------
# Processing of subfile hashes and convert to vector
#----------------------------------------------------


#parse entry in format hash filename offset start-end
md5deep_subfile_re = re.compile("([0-9abcdef]+)\s+(\S.+)\soffset\s(\d+)-(\d+)$")

def parse_md5deep_subfile_entry(text) :
    """processing of individual subfile block hash line in md5deep"""
    try:
        parse = md5deep_subfile_re.search(text)
        # not sure what `other` is supposed to represent
        c, other, r1, r2 = parse.groups() # <-- could raise an exception here
        a_dictionary = {'c': c, 'r': '_{}_{}'.format(r1, r2)}
        return (a_dictionary, other)
    except:
        raise ValueError('bad sub file entry: ' + text)


def construct_vector(name, hash_set, dup_map, fnamemap, checksummap):
    if name in dup_map:     #skipping -- duplicate
        return False
    if len(hash_set) < 2:  #skipping -- empty or singleton
        return False
    return [fnamemap.get_id(name),
            map(checksummap.get_id, hash_set)]


def construct_subhash_vectors(lines, dup_map):
    """collect set of checksums per file, substituting numeric id (fno, hno) for text values"""
    result = {}
    fnamemap = FnameMap()
    checksummap = ChecksumMap()

    for line in lines:
        (val, name) = parse_md5deep_subfile_entry(line)
        if not result.has_key(name):
            result[name] = []
        result[name].append(val)
    
    result2 = []
    for (name, vals) in result.items():
        something = construct_vector(name, vals, dup_map, fnamemap, checksummap)
        if something:
            result2.append(something)
        
    return (result2, fnamemap, checksummap)


def prune_vectors(vector_set, min_blocks, checksummap) :
    """only keep vectors containing at least 1 shared checksum"""
    result = []
    for fno, hset in vector_set:
        newset = []
        for hno in hset:
            if checksummap.get_count(hno) > 1:
                newset.append(hno)
        if len(newset) >= min_blocks:
            result.append([fno, newset])   
    return result

       
def generate_subfile_vectors(dsub_file, duplicates, min_blocks):
    """top level routine - convert file checksums to vectors, pruning non-shared entries"""   
    dup_map = create_duplicate_map(duplicates)
    (vector_set, fnamemap, checksummap) = construct_subhash_vectors(dsub_file, dup_map)
    pruned_vector_set = prune_vectors(vector_set, min_blocks, checksummap)
    return pruned_vector_set
