import networkx as nx
from networkx.algorithms import bipartite
import uuid


#----------------------------
# Clustering and Subgraph Optimization
#----------------------------

def find_conflicting_checksums(csums, graph, checksummap):
    """find those block checksums that map to the same file region"""
    range_sets = {}
    for hno in csums:
        raise ValueError('oops, hno is something like `(.*):(.*)`, and we want to use the second part to look up the hval')
        range_val = checksummap.get_hval(hno)['r']
        if range_val in range_sets:
            range_sets[range_val].append(hno)
        else:
            range_sets[range_val] = [hno]

    compatible = [value[0] for key, value in range_sets.items() if len(value) == 1]
    # a bit confusing:  `sum` is used to merge list of lists
    conflicting = sum([value for key, value in range_sets.items() if len(value) > 1], [])
    # a dictionary comprehension ???
    ranges = {key: value for key, value in range_sets.items() if len(value) > 1}
    return compatible, conflicting, ranges


def path_pairs(path):
    """Converts path into a set of node pairs"""
    pairs = zip(path, path[1:])
    reverse_sorted_pairs = map(lambda xs: tuple(sorted(xs, reverse=True)), pairs)
    return set(reverse_sorted_pairs)


def path_intersection(paths):
    """finds common segments among a set of paths:
    takes the paths in pairwise order:  from 'abcde' , it looks at 'ab', 'bc', 'cd', and 'de' """
    result = []
    for path1, path2 in zip(paths, paths[1:]):
        common = path1.intersection(path2)
        if len(common) > 0:
            result.append(list(common))
    return result


def process_subgraph(graph, files, csums):
    """
    what does this return?
    """
    _, conflicting_csums, conflict_details = find_conflicting_checksums(csums, graph)

    if len(conflict_details) > 0:
        # create sub-graph with conflicting csums and fill set of files       
        new_graph = nx.subgraph(graph, files + conflicting_csums)
        partitions = nx.connected_components(new_graph)

        while len(partitions) == 1:
            # break-up monolithic partition -- find paths between conflict pairs and break shortest path.
            paths = []
            for src, target in conflict_details.values():
                paths.append(path_pairs(nx.shortest_path(new_graph, src, target)))

            common_paths = path_intersection(paths)

            # for now, just break the first path and interate.  In future, may want to break multiple paths at once
            if len(common_paths) == 0 or len(common_paths[0]) == 0:
                raise ValueError('Error: Unexpected result - shoud be at least 1 common path pair')
            pair = common_paths[0][0]    # arbitrarily pick first segment
            new_graph.remove_edge(pair[0], pair[1])
            partitions = nx.connected_components(new_graph)
            _, conflicting_csums, conflict_details = find_conflicting_checksums(csums, new_graph)
            
        subgroups = process_partitions(partitions, new_graph)
    else:
        # no further sub-graphs
        subgroups = []

    #now compute combined result for group and its subgroups
    subgroup_csums, subgroup_files, tally = [], [], 0
    for subgroup in subgroups:
        subgroup_csums.extend(subgroup['csums'])
        subgroup_files.extend(subgroup['files'])
        tally += subgroup['savings']
    for csum in csums:
        tally += len(nx.edges(graph, csum)) - 1

    return {
        'selected_files': set(files) - set(subgroup_files),
        'selected_csums': set(csums) - set(subgroup_csums),
        'savings'       : tally,
        'subgroups'     : subgroups
    }


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
