#!/usr/bin/python3

import argparse
import sys,os,random
from datetime import datetime
    
aig_sweep = "&scorr;&sweep;"
#aig_permute_in = ["", "&dfs", "&dfs -n", "&dfs -r", "&dfs -n -r"]
aig_permute_in = [""]
# aig_zero_cost_replace_ops = ["",
#                "&put;resub -K 8 -N 2 -z;&get -n;", "&put;resub -K 8 -N 3 -z;&get -n;",
#                "&put;resub -K 12 -N 2 -z;&get -n;", "&put;resub -K 12 -N 3 -z;&get -n;",
#                "&put;resub -K 16 -N 2 -z;&get -n;", "&put;resub -K 16 -N 3 -z;&get -n;"]

#aig_zero_cost_replace_ops = ["", "&put;resub -z;&get;"]
aig_zero_cost_replace_ops = ["", ""]
# aig_ind_ops = ["&dc2", "&syn2", "&b", "&b -d",
#                "&put;resub -K 8 -N 2;&get", "&put;resub -K 8 -N 3;&get",
#                "&put;resub -K 12 -N 2;&get", "&put;resub -K 12 -N 3;&get",
#                "&put;resub -K 16 -N 2;&get", "&put;resub -K 8; &get",
#                "&if -W 300 -x", "&if -W 300 -g"]
aig_ind_ops = ["&dc2", "&syn2", "&b", "&b -d",
               "&if -W 300 -x", "&if -W 300 -g"]
aig_ch_ops = ["&synch2", "&dch", "&dch -f"]


# old stuff
options = ["rewrite", "rewrite -z", "refactor", "refactor -z", "resub -K 8", "resub -K 4", "resub -K 12", "resub -N 0", "resub -N 2", "resub -N 3", "balance",  "dc2"]

opener = "strash;ifraig;scorr;"
# closure_ftune = "strash;ifraig;scorr;dc2;strash;dch -f;if -K 6;mfs2;lutpack -S 1"
closure_whitebox_delay = "strash;ifraig;scorr;strash;dch -f;if -v;mfs2;print_stats -l"
closure = "dretime; strash; dch -f; if -v; mfs2" # LUTPACK or not; dretime or not with -

def parse_index(idx):
    i = idx

    # Ordering of Inputs and Vars
    perm_idx = i % len(aig_permute_in)
    i = i // len(aig_permute_in)

    # Structural choice AIG optimization options
    ch_idx = i % len(aig_ch_ops)
    i = i // len(aig_ch_ops)

    # # Step 1.5. (optional) add zero-cost replacement
    # zero_cost_idx = i % len(aig_zero_cost_replace_ops)
    # i = i // len(aig_zero_cost_replace_ops)
    
    # Tech Indepdent AIG rewriting optimization options
    ind_idx = []
    while i >= 0 :
        num_options = len(aig_ind_ops)
        remainder = i % num_options
        divisor = i // num_options
        ind_idx.append(remainder)
        if divisor <= 0 : 
            break;
        else : 
            i = divisor-1
    return ind_idx, ch_idx, perm_idx

def new_get_seq_abc9(idx, lib_num):
    seq = aig_sweep
    i = idx
    ind_idx, ch_idx, perm_idx = parse_index(idx)
    
    # Step 1 and 1.5: Tech Ind AIG rewriting
    seq += aig_permute_in[perm_idx] + ";"
    for op in ind_idx:
        seq += aig_ind_ops[op] + ";"
        
    # Step 2. Structural choice based rewriting
    seq += aig_ch_ops[ch_idx] + ";"
    if lib_num > 0:
        seq +="&if -W 300 -v;&mfs;"
    else:
        seq +="&if -W 300 -K 6 -v;&mfs;"

    return seq

def get_seq(idx): 
    num_options = len(options) 
    seq = opener
    i = idx
    while idx >= 0:
        remainder = i % num_options
        divisor = i // num_options
        seq += options[remainder] + ";"
        if divisor <= 0 : 
            break;
        else : 
            i = divisor
    seq += closure_whitebox_delay
    return seq

def get_seq_abc9(idx): 
    num_options = len(options_abc9)
    seq = opener_abc9
    i = idx
    while idx >= 0:
        remainder = i % num_options
        divisor = i // num_options
        seq += options_abc9[remainder] + ";"
        if divisor <= 0 : 
            break;
        else : 
            i = divisor
    seq += closure_abc9
    return seq


def get_seq_abc9_w_perm(idx): 
    num_options = len(options)
    seq = "&scorr;&sweep;&put;"
    i = idx
    while idx >= 0:
        remainder = i % num_options
        divisor = i // num_options
        seq += options[remainder] + ";"
        if divisor <= 0 : 
            break;
        else : 
            i = divisor
    seq += "&get;&dch -f; &ps; &if -W 300 -v; &mfs;"
    return seq

def get_rand_seq(seq_len): 
    num_options = len(options) 
    seq = opener

    random.seed(datetime.now())
    for i in range(seq_len) :
        r = random.randint(0, num_options)
        if r < num_options :
            seq += options[r] + ";"
    seq += closure_whitebox_delay
    return seq

def get_rand_seq_abc9(seq_len): 
    num_options = len(options_abc9) 
    seq = opener_abc9

    random.seed(datetime.now())
    for i in range(seq_len) :
        r = random.randint(0, num_options)
        if r < num_options :
            seq += options_abc9[r] + ";"
    seq += closure_abc9
    return seq

def main():
    parser = argparse.ArgumentParser(
            description='Create ABC script for each permuted sequence of synthesis transformations')
    parser.add_argument('--random_seq_len', type=int, default=0, help='Random: length of target sequence')
    parser.add_argument('--in_idx', type=int, help='Index of current sequence', default=-1)
    parser.add_argument('--abc9', type=int, help='Whether or not run ABC9', default=0)
    parser.add_argument('--lut_library', type=int, help='Index of LUT Library to use: 0 is default', default=0)
    args = parser.parse_args()

    do_abc9 = args.abc9 > 0
    do_random = args.random_seq_len > 0
    lut_lib_num = args.lut_library
    
    if lut_lib_num > 0:
        print("read_lut " + os.path.dirname(os.path.abspath(__file__)) + "/lut_library/LUTLIB_{}.txt".format(lut_lib_num))

    if do_random:
        if do_abc9:
            print(get_rand_seq_abc9(args.random_seq_len))
        else:
            print(get_rand_seq(args.random_seq_len))
    elif do_abc9:
        #print(get_seq_abc9_w_perm(args.in_idx))
        print(new_get_seq_abc9(args.in_idx, lut_lib_num))
    else :
        print(get_seq(args.in_idx))

if __name__ == '__main__':
    main()    
