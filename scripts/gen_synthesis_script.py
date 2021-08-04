#!/usr/bin/python3

import argparse
import sys,os,random

abc9=True
options = ["rewrite", "rewrite -z", "refactor", "refactor -z", "resub -K 8", "resub -K 4", "resub -K 12", "resub -N 2", "resub -N 3", "balance",  "dc2"]
options_abc9 = ["&dc2", "&shrink", "&syn2", "&synch2", "&retime"]

opener = "strash;ifraig;scorr;"
opener_abc9 = "&scorr;&sweep;"

# closure_ftune = "strash;ifraig;scorr;dc2;strash;dch -f;if -K 6;mfs2;lutpack -S 1"
closure_whitebox_delay = "strash;ifraig;scorr;strash;dch -f;if -v;mfs2;print_stats -l"
closure = "dretime; strash; dch -f; if -v; mfs2" # LUTPACK or not; dretime or not with -
closure_abc9 = "&dch -f; &ps; &if -W 300 -v; &mfs; &ps -l"

def get_sequence(idx): 
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

def get_sequence_abc9(idx): 
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

def get_random_sequence(seq_len): 
    num_options = len(options) 
    seq = "strash;"

    random.seed()
    for i in range(seq_len) :
        r = random.randint(0, num_options)
        if r <0 :
            seq += options[r] + ";"
    seq += closure_whitebox_delay
    return seq


def main():
    parser = argparse.ArgumentParser(
            description='Create ABC script for each permuted sequence of synthesis transformations')
    parser.add_argument('--random_seq_len', type=int, default=0, help='Random: length of target sequence')
    parser.add_argument('--in_idx', type=int, help='Index of current sequence')
    args = parser.parse_args()

    if args.random_seq_len > 0:
        print(get_random_sequence(args.random_seq_len))
    elif abc9:
        print(get_sequence_abc9(args.in_idx))
    else :
        print(get_sequence(args.in_idx))

if __name__ == '__main__':
    main()    