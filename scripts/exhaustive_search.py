#!/usr/bin/python3

import argparse
import sys,os,random

options = ["rewrite", "rewrite -z", "refactor", "refactor -z", "resub -K 8", "resub -K 4", "resub -K 12", "resub -N 2", "resub -N 3", "balance",  "dc2"]
closure = "strash;ifraig;scorr;dc2;strash;dch -f;if -K 6;mfs2;lutpack -S 1"
closure_whitebox_delay = "strash;ifraig;scorr;dc2;strash;dch -f;if -v;mfs2;print_stats"

def get_sequence(idx): 
    num_options = len(options) 
    seq = "strash;"
    i = idx
    while True:
        remainder = i % num_options
        divisor = i // num_options
        seq += options[remainder] + ";"
        if divisor <= 0 : break;
        else : i = divisor
    seq += closure_whitebox_delay
    return seq

def get_random_sequence(seq_len): 
    num_options = len(options) 
    seq = "strash;"

    random.seed()
    for i in range(seq_len) :
        r = random.randint(0, num_options)
        if r < num_options:
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
    else:
        print(get_sequence(args.in_idx))

if __name__ == '__main__':
    main()    