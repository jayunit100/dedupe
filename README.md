Dedupe
======
Note:  Code is currently a work in progress.

Python-based tool to detect deduplication candidates for inline dedupe.  Includes support both whole-file and sub-block use-cases.

Tool bases anaylyis on a set-of MD5 checksum files, who file and sub-file, computed using md5deep or equivalent. To simplify analysis, whole-file checksums should be sorted by checksum prior to analysis.  Commands necessary to compute checksums is shown below:

     md5deep -r -o f /Users/doug > file_hashes.out
     md5deep -r -o f -p 1m /Users/doug > file_1m_subhashes.out
     sort --key=1,32 file_hashes.out > file_hashes_sorted.out
     
     Note(s):  
       1) md5deep can be found at: http://md5deep.sourceforge.net/
       2) Alternative checksums, such as SHA256 can be used.  If so, 
          sort command key parameter may need to be modified to reflect checksum width      

Command line
     Usage: dedupe.py [options] whole_checksums [sorted_block_checksums]

     Options:
       -h, --help            show this help message and exit
       -c TYPE, --checksum_type=TYPE
                             format of checksum in input file, where checksum TYPE
                             is MD% or SHA256
       -v, --dump_vectors
                             enables dumping of vectors to .vectors file for use
                             with alternative analysis
       -s, --status          prints status information to console
       -d, --debug           logs information to console for debug purposes
       -g, --show_graph      displays sub-graphs to console for debug purposes


Generall Approach

1) Gather whole-file and sub-file signatures (MD5). See above.

2) Identify same-file dedupe candidates.  Since file signatures were pre-sorted by signature, dedupes are simply sequences of files sharing the same signature

3) Identify sub-file dedupe candidates
   A) Compute vectors (edge sets)
       i)  map file names and unque signatures to numbers to reduce
           data footprint during subsequent processing
      ii) Filter vector set
          a) Single block files (single signature) since these are already 
             covered by file-level dedupe
          b) Only one vector per same-file duplicates set
          c) remove singleton signatures -- sub-file hash must be
             present in multiple files to be relevant for subsequent
             graph based analusis
   B) Graph based analysis using Networkx
       i)   Construct bipartite graph nodes =(files, checksums)
      ii)  Identify connected sub-graphs
     iii) Optimize sub-graphs


