from optparse import OptionParser
from . import dedupe
from . import graphanalysis


def build_parser():
    parser = OptionParser(usage="usage: %prog [options] whole_checksums [sorted_block_checksums]")
    parser.add_option("-m", "--min_blocks", type = 'int', default = 2, dest="min_blocks",
                      help="minimum number of BLOCKS that a file must share to be considered a candidate for dedupe",
                      metavar="BLOCKS")   
    return parser


def doALotOfStuff():
    parser = build_parser()
    (options, args) = parser.parse_args()
    if args:
        d_file = args[0]
        duplicates = dedupe.find_duplicateFiles(d_file, json_duplicates_fname=d_file)
        print duplicates
        if len(args) == 2: # what if len(args) > 2?
            dsub_file = args[1]
            vector_set = dedupe.generate_subfile_vectors(dsub_file, duplicates, options.min_blocks)
            dedupe_groups = graphanalysis.graph_analysis(vector_set)
            print dedupe_groups
    else:
        raise ValueError('missing input files')


if __name__=="__main__":
    doALotOfStuff()
