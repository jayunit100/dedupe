import sys
import networkx as nx
from networkx.algorithms import bipartite
import string
import re
import uuid
from optparse import OptionParser
import itertools
from fname_map import FnameMap
from fname_map import ChecksumMap


#--------------------------------------
# File level deduplication
#--------------------------------------

#parse entry in format hash filename
md5deep_file_re    = re.compile("([0-9abcdef]+)\s+(\S.+)$")

def parse_md5deep_file_entry(text) :
    """parses individual lines from md5deep"""
    try:
        parse = md5deep_file_re.search(text)
        return(parse.groups()[0],  # <-- can raise exception if regex doesn't match
               parse.groups()[1])
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
    parse = md5deep_subfile_re.search(text)
    if parse:
        return({'c': parse.groups()[0],
                'r':'_{}_{}'.format(parse.groups()[2], parse.groups()[3])},
               parse.groups()[1])               
    else:
        raise ValueError('bad sub file entry: ' + text)


def construct_vector(name, hash_set, dup_map):
    if name == "" :         #skipping - no file
        return False
    if name in dup_map:     #skipping -- duplicate
        return False
    if len(hash_set) < 2 :  #skipping -- empty or singleton
        return False
    return [FnameMap.get_id(name),
            [ChecksumMap.get_id(hval) for hval in hash_set]]


def construct_subhash_vectors(fname, dup_map):
    """collect set of checksums per file, substituting numeric id (fno, hno) for text values"""

    result = []    
    FnameMap.reset()        #initialize mapping tables
    ChecksumMap.reset()

    fd = open(fname)
    last_name = ""
    hash_set = []
    for text in fd:
        (val, name) = parse_md5deep_subfile_entry(text)
        
        if name != last_name:
            vec = construct_vector(last_name, hash_set, dup_map)
            if vec:
                result.append(vec)
            last_name = name
            hash_set = []
            
        hash_set.append(val)
        
    vec = construct_vector(name, hash_set, dup_map)
    if vec:
        result.append(vec)
    fd.close()
    return result

def prune_vectors(vector_set, min_blocks) :
    """only keep vectors containing at least 1 shared checksum"""
    result = []
    
    for fno, hset in vector_set:
        newset = []
        for hno in hset:
            if ChecksumMap.get_count(hno) > 1:
                newset.append(hno)
        if len(newset) >= min_blocks:
            result.append([fno, newset])   
    return result

       
def generate_subfile_vectors(dsub_file, duplicates, min_blocks):
    """top level routine - convert file checksums to vectors, pruning non-shared entries"""   
    dup_map = create_duplicate_map(duplicates)
    vector_set = construct_subhash_vectors(dsub_file, dup_map)
    pruned_vector_set = prune_vectors(vector_set, min_blocks)
    return pruned_vector_set

#----------------------------
# Clustering and Subgraph Optimization
#----------------------------

def find_conflicting_checksums(csums, graph):
    """find those block checksums that map to the same file region"""
    range_sets = {}
    for hno in csums:
        range_val = ChecksumMap.get_range_using_encoded_id(hno)
        if range_val in range_sets:
            range_sets[range_val].append(hno)
        else:
            range_sets[range_val] = [hno]

    compatible = [value[0] for key, value in range_sets.items() if len(value) == 1]
    # a bit confusing:  `sum` is used to merge list of lists
    conflicting = sum([value for key, value in range_sets.items() if len(value) > 1],[])
    # a dictionary comprehension ???
    ranges = {key: value for key, value in range_sets.items() if len(value) > 1}
    return compatible, conflicting, ranges

def path_pairs (path):
    """Converts path into a set of node pairs, where pairs are encoded as a _ delimitted string"""
    result = []
    for i, node1 in enumerate(path, start=1):
        if i <len(path):
            node2 = path[i]
            if node1 > node2:
                result.append('{}_{}'.format(node1, node2))    #hack to make set intersection work
            else:
                result.append('{}_{}'.format(node2, node1))
    return (set(result))
            
def path_intersection(paths):
    """finds common segments among a set of paths"""
    result = []
    for i, path1 in enumerate(paths, start=1):
        if i < len(paths):
            path2 = paths[i]
            common = path1.intersection(path2)
            if len(common) > 0:
                pairs = []
                for node_pair_enc in common:
                    pairs.append(node_pair_enc.split('_'))  #unencode node pair
                result.append(pairs)
    return result
            
def process_subgraph(graph, dedupe_group) :
    files = dedupe_group['files']
    csums = dedupe_group['csums']
    
    global display_graph_flag   
    if display_graph_flag:
        print 'Bipartite Sub-Graph'
        nx.draw(graph)
        plt.show()
    common_csums, conflicting_csums, conflict_details = find_conflicting_checksums(csums, graph)

    if len(conflict_details) > 0:
        # create sub-graph with conflicting csums and fill set of files       
        new_graph = nx.subgraph(graph, files + conflicting_csums)
        partitions = nx.connected_components(new_graph)
        if  display_graph_flag:
            nx.draw(new_graph)
            plt.show()

        while len(partitions) == 1:
            #break-up monolithic partition -- find paths between conflict pairs and break shortest path.
            paths = []
            for src, target in conflict_details.values():
                paths.append(path_pairs(nx.shortest_path(new_graph, src, target)))

            common_paths = path_intersection(paths)

            #for now, just break the first path and interate.  In future, may want to break multiple paths at once
            if len(common_paths) == 0 or len(common_paths[0]) == 0:
                raise ValueError('Error: Unexpected result - shoud be at least 1 common path pair')
            pair = common_paths[0][0]    #arbitrarily pick first segment
            new_graph.remove_edge(pair[0], pair[1])
            partitions = nx.connected_components(new_graph)
            common_csums, conflicting_csums, conflict_details = find_conflicting_checksums(csums, new_graph)
            
        subgroups = process_partitions(partitions, new_graph)
        dedupe_group['subgroups'] = subgroups

    else:
        # no further sub-graphs
        dedupe_group['subgroups'] = []

    #now compute combined result for group and it's subgroups
    subgroup_csums = []
    subgroup_files = []
    tally = 0
    for subgroup in dedupe_group['subgroups']:
        for csum in subgroup['csums']:
            subgroup_csums.append(csum) 
        for fname in subgroup['files']:
            subgroup_files.append(fname) 
        tally += subgroup['savings']
    dedupe_group['selected_files'] = set(dedupe_group['files']) - set(subgroup_files)
    dedupe_group['selected_csums'] = set(dedupe_group['csums']) - set(subgroup_csums)
    for csum in csums:
        tally += len(nx.edges(graph, csum)) - 1
    dedupe_group['savings'] = tally
    return dedupe_group

def optimize_dedupe_group(dedupe_group):
    # NOT YET IMPLEMENTED
    # adds direct_files, direct_groups direct_csums fields
    #promots one (or more compatible) entry of each sub-group as direct, based on savings
    return dedupe_group


def process_partitions(partitions, graph, singleton_filter=False ) :
    """processing of individual sub-graph"""
    dedupe_groups = []
    for part in partitions:
        files = [nodenum for nodenum in part if nodenum[0] == 'F']
        csums = [nodenum for nodenum in part if nodenum[0] == 'H']

        if (len(files) > 1) or (not singleton_filter):  #only sub-graphs with multiple files
            subgraph = nx.subgraph(graph, part)            
            dedupe_group = {'name':str(uuid.uuid4()), 'files':files, 'csums':csums}
            dedupe_group = process_subgraph(subgraph, dedupe_group)
            dedupe_group = optimize_dedupe_group(dedupe_group)
            dedupe_groups.append(dedupe_group)
    return dedupe_groups


def build_graph_from_vectors(vector_set, show_subgraph=False) :
    """creates top-level fraph from set of vectors"""
    B = nx.Graph()
    for fno, hset in vector_set:
        B.add_node(FnameMap.encode(fno), bipartite=0)
        for hno in hset:
            if hno not in B:
                B.add_node(ChecksumMap.encode(hno), bipartite=1)               
            B.add_edge(FnameMap.encode(fno), ChecksumMap.encode(hno))
    return B


def resolve_file_names(files):
    return map(FnameMap.get_name_using_encoded_id, files)

def resolve_csums(csums):
    return map(ChecksumMap.get_hval_using_encoded_id, csums)

def annotate_group(group):
    new_group = {
        'csums'         : resolve_csums(group['csums']),
        'selected_csums': resolve_csums(group['selected_csums']),
        'files'         : resolve_file_names(group['files']),
        'selected_files': resolve_file_names(group['selected_files']),
        'subgroup'      : map(annotate_group, group['subgroups'])
    }
    
    for key in group.keys():
        if key not in ['csums', 'selected_csums', 'files', 'selected_files', 'subgroup']:
            new_group[key] = group[key]

    return new_group

def graph_analysis(vector_set) :
    """top level routine, partitions vector sets and identified common parent for a set of files"""

    B = build_graph_from_vectors(vector_set)
    partitions = nx.connected_components(B)
    dedupe_groups = process_partitions(partitions, B, singleton_filter = True)
    return map(annotate_group, dedupe_groups)


           
#------------------------------------
# Main
#------------------------------------

def build_parser():
    parser = OptionParser(usage="usage: %prog [options] whole_checksums [sorted_block_checksums]")
    parser.add_option("-c", "--checksum_type", type = 'string', default = "MD5", dest="hash_type",
                      help="format of checksum in input file, where checksum TYPE is MD% or SHA256",
                      metavar="TYPE")
    parser.add_option("-m", "--min_blocks", type = 'int', default = 2, dest="min_blocks",
                      help="minimum number of BLOCKS that a file mush share to be considered a candidate for dedupe",
                      metavar="BLOCKS")   
    parser.add_option("-v", "--dump_vectors", default=False, action="store_true", dest="dump_vectors",
                      help="enables dumping of vectors to .vectors file for use with alternative analysis")
    parser.add_option("-d", "--debug", default=False, action="store_true", dest="debug",
                      help="logs information to console for debug purposes")    
    parser.add_option("-g", "--show_graph", default=False, action="store_true", dest="show_graphs",
                      help="displays sub-graphs to console for debug purposes")
    return parser


def doALotOfStuff():
    parser = build_parser()
    (options, args) = parser.parse_args()
    
    global display_graph_flag
    global debug

    enable_subfile_analysis = True
    
    debug = options.debug
    min_blocks = options.min_blocks
    display_graph_flag = options.show_graphs
    if args:
        d_file = args[0]
        if len(args) == 2:
            dsub_file = args[1]
            enable_subfile_analysis = True
        else:
            enable_subfile_analysis = False
    else:
        raise ValueError('missing input files')
        
    (d_file_base, ext) = string.rsplit(d_file, '.', 1)
    jdup_fname = d_file_base + '.json'      
    duplicates = find_duplicateFiles(d_file, json_duplicates_fname=jdup_fname)

    if enable_subfile_analysis:
        (d_subfile_base, ext) = string.rsplit(dsub_file, '.', 1)
        jvec_fname = False
        lvec_fname = False
        if options.dump_vectors:
            jvec_fname = d_subfile_base + '.vect.json' #Should this option be deleted?
            lvec_fname = d_subfile_base + '.vectors'
   
        vector_set = generate_subfile_vectors(dsub_file, duplicates, min_blocks,
                                              json_vectorset_fname=jvec_fname,
                                              list_vectorset_fname=lvec_fname)
        dprint('graph analysis')
        dedupe_groups = graph_analysis(vector_set)
        dpprint(dedupe_groups)
        dedupe_out_fname = d_subfile_base + '.dedupe.json'
        print 'Outputting dedupe groups in JSON format to: {}'.format(dedupe_out_fname)
        jdump(dedupe_groups, dedupe_out_fname, pretty=True)


if __name__=="__main__":
    doALotOfStuff()