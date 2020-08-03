#!/usr/bin/python3

import argparse
import collections
import csv
import os
import re
import sys

import functools
import operator

#import matplotlib
#matplotlib.use('gtk3agg')
#
import matplotlib.pyplot as plt
import numpy as np

TEST_DIR_RE = re.compile(
    r'tab_(vivado|yosys|yosys-abc9)_([a-zA-Z0-9_.]+)_([a-zA-Z0-9]+)_([a-zA-Z0-9]+)')
TEST_RESULT_FILE_RE = re.compile(r'test_(\d+).txt')


class LineMatcher:

    def __init__(self):
        self.matchers = []

    def AddMatcher(self, key, matcher):
        self.matchers.append((key, matcher))

    def MatchText(self, line):
        """Returns key and re.Match object matching line."""
        for key, pattern in self.matchers:
            match = pattern.match(line)
            if match:
                return key, match
        return None, None


class RegexResult:
    def __init__(self, label_queue, match_generator):
        # We expect to match each label once and in the given order,
        # so that we can stop looking for one as soon as we match it, and
        # start looking for the next one. They must be in the order they appear
        # in the file. Where multiple labels should be matched in any order at
        # once, we expect a tuple of labels in this queue.
        self.line_matchers = collections.deque()
        if not label_queue or not match_generator:
            raise RuntimeError(
                'bad regex result. label_queue: {} match_generator: {}'.format(
                label_queue, match_generator))
        for label in label_queue:
            matcher = LineMatcher()
            if isinstance(label, tuple):
                for entry in label:
                    matcher.AddMatcher(entry, match_generator(entry))
            else:
                matcher.AddMatcher(label, match_generator(label))
            self.line_matchers.append(matcher)
        self.matcher = self.line_matchers.popleft()
        self.results = dict()

    def MatchNext(self, text):
        key, match = self.matcher.MatchText(text)
        if match:
            self.results[key] = match.groups()
            if self.line_matchers:
                self.matcher = self.line_matchers.popleft()

    def GetLabel(self, label):
        if label not in self.results:
            raise ValueError(
                    'missing results for label: {}'.format(label))
        return self.results[label]


class UtilizationResult(RegexResult):
    ## | CLB LUTs                   | 4455 |     0 |    203128 |  2.19 |
    ## | Bonded IOB       |  366 |     0 |       520 | 70.38 |
    @staticmethod
    def Match4ColumnRow(label):
        spec = (r'^\|\s+(' + label +
                r')\s+\|\s+(\d+)?\s+\|\s+(\d+)?\s+\|\s+(\d+)?\s+\|\s+(<?\d+.\d+)?\s+\|$')
        return re.compile(spec)

    # TODO(aryap): Integrate
    @staticmethod
    def Match3ColumnRow(label):
        spec = (r'^\|\s+(' + label +
                r')\s+\|\s+(\d+)?\s+\|\s+(\d+)?\s+\|\s+(\S+)\s+\|$')
        return re.compile(spec)

    # Match labels in the file in the order they appear here. Where there is a
    # tuple, all of the labels in the tuple are searched for on each line of
    # the file.
    LABELS= [('CLB LUTs', 'Slice LUTs', 'LUT as Logic', 'LUT as Memory',
              'LUT as Shift Register', 'Slice Registers', 'Register as Flip Flop',
              'Register as Latch', 'Block RAM Tile', 'Bonded IOB')]

    def __init__(self):
        super().__init__(UtilizationResult.LABELS,
                         UtilizationResult.Match4ColumnRow)


class RuntimeResult(RegexResult):
    #place_design: Time (s): cpu = 00:01:52 ; elapsed = 00:01:53 . Memory (MB): peak = 2723.559 ; gain = 68.660 ; free physical = 86733 ; free virtual = 123087
    @staticmethod
    def MatchTimeRow(label):
        spec = (r'^(' + label +
                r'):.*cpu = (\d{2}:\d{2}:\d{2}).*peak = (\d+\.\d+).*$')
        return re.compile(spec)

    LABELS = ['place_design', 'route_design']
    def __init__(self):
        super().__init__(RuntimeResult.LABELS,
                         RuntimeResult.MatchTimeRow)

class TimingResult(RegexResult):
    @staticmethod
    def MatchSlackMetOrNot():
        spec = (r'^Slack \(([A-Z]+)\).*$')
        return re.compile(spec)

    def MatchCriticalPathSlack():
        spec = (r'^\s+slack\s+(-?\d+\.\d+)\s+$')
        return re.compile(spec)

    def __init__(self):
        LABELS = {
            1: TimingResult.MatchSlackMetOrNot(),
            2: TimingResult.MatchCriticalPathSlack()
        }

        super().__init__(LABELS, lambda x: LABELS[x])


class ConstraintResult:

    def __init__(self, file_path):
        self.file_path = file_path
        self.util = None
        self.timing = None
        self.runtime = None


class Result:

    def __init__(self, synth_method, ip, device, grade, path):
        self.synth_method = synth_method
        self.ip = ip
        self.device = device
        self.grade = grade
        self.path = path
        # This should be a dict of constraint: ConstraintResult
        self.constraints = dict()
    
    def __repr__(self):
        return '({}-{}) {}, {} '.format(
            self.device, self.grade, self.ip, self.synth_method)

    def GetConstraintResult(self, constraint):
        if constraint not in self.constraints:
            raise ValueError('missing results for constraint: {}'.format(
                    constraint))
        if constraint is None:
            raise ValueError('should not have None constraint: {}'.format(
                    constraint))
        return self.constraints[constraint]

    # TODO(aryap): Refactor between this and GetUtilizationResult!
    def GetRuntimeResult(self, constraint, label):
        try:
            constr = self.GetConstraintResult(constraint)
            if constr.runtime is None:
                raise ValueError('missing results for runtime'.format(
                    repr(self)))
            return constr.runtime.GetLabel(label)
        except ValueError as err:
            print('{} {}, see {}'.format(
                repr(self), err, self.path), file=sys.stderr)
            return None

    def GetUtilizationResult(self, constraint, label):
        try:
            constr = self.GetConstraintResult(constraint)
            if constr.util is None:
                raise ValueError('missing results for utilisation'.format(
                    repr(self)))
            return constr.util.GetLabel(label)
        except ValueError as err:
            print('{} {}, see {}'.format(
                repr(self), err, self.path), file=sys.stderr)
            return None

    def GetTimingResult(self, constraint, label):
        try:
            constr = self.GetConstraintResult(constraint)
            if constr.util is None:
                raise ValueError('missing results for utilisation'.format(
                    repr(self)))
            return constr.timing.GetLabel(label)
        except ValueError as err:
            print('{} {}, see {}'.format(
                repr(self), err, self.path), file=sys.stderr)
            return None


    def ParseResults(self):
        for f in os.listdir(self.path):
            match = TEST_RESULT_FILE_RE.match(f)
            if (match):
                constraint = match.group(1)
                result_file = os.path.join(self.path, f)
                self.constraints[constraint] = ConstraintResult(result_file)

        for constraint, constraint_result in self.constraints.items():
            util = UtilizationResult()
            runtime = RuntimeResult()
            timing = TimingResult()
            with open(constraint_result.file_path) as f:
                for i, line in enumerate(f):
                    util.MatchNext(line)
                    runtime.MatchNext(line)
                    timing.MatchNext(line)
            constraint_result.util = util
            constraint_result.runtime = runtime
            constraint_result.timing = timing


def MakePrettyGraphs(results):
    fig, ax = plt.subplots()

    width = 0.35
    x_labels = []

    synth_method_list = sorted(synth_methods)
    device_and_grade = ('xc7a200', '1')
    for ip_name, result_by_synth_method in synth_results.items():
        for method_fetch, match_group, labels in metrics:
            label = 'Slice LUTs'
            for method in synth_method_list:
                if method in result_by_synth_method:
                    value = result_by_synth_method[method].GetUtilizationResult(constr, label)
                    line.append(
                            value[match_group] if value else value_if_no_result)
                else:
                    line.append(value_if_no_result)


def main():
    parser = argparse.ArgumentParser(
            description='Collect synthesis benchmark results from a given directory')
    parser.add_argument('--from_dir', type=str, help='Results directory')
    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
        parser.exit()
        
    source_dir = None
    try:
        source_dir = os.path.realpath(args.from_dir)
    except:
        print('Could not find results in {}'.format(source_dir), file=sys.stderr)
        sys.exit(1)

    results = []
    ips = set()
    synth_methods = set()
    results_by_device = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(None)))
    for d in os.listdir(source_dir):
        match = TEST_DIR_RE.match(d)
        if match:
            result = Result(*match.groups(), os.path.join(source_dir, d))
            results.append(result)
            results_by_device[(result.device, result.grade)][result.ip][
                    result.synth_method] = result
            synth_methods.add(result.synth_method)
            ips.add(result.ip)
            result.ParseResults()
        else:
            print('Could not parse result dir name: {}'.format(d))

    print('Scanned {} result files'.format(len(results)))
    print('Found {} IP(s); {} synth method(s)'.format(
        len(ips), len(synth_methods)))

    value_if_no_result = 'none'
    # These vary by device.
    metrics = [
            # 1 is the index of the 'number used' column in each output row of
            # the Vivado results
            (lambda x: x.GetUtilizationResult, 1,
                ['CLB LUTs', 'Slice LUTs', 'LUT as Logic', 'LUT as Memory',
                  'LUT as Shift Register', 'Slice Registers', 'Register as Flip Flop',
                  'Register as Latch', 'Block RAM Tile', 'Bonded IOB']),
                  #'LUT6', 'LUT5', 'LUT4', 'LUT3', 'LUT2', 'LUT1']),
            (lambda x: x.GetRuntimeResult, 1,
                ['place_design', 'route_design']),
            (lambda x: x.GetRuntimeResult, 2,
                ['place_design', 'route_design']),
            (lambda x: x.GetTimingResult, 0,
                    [1, 2])]

    synth_method_list = sorted(synth_methods)
    for device_and_grade, synth_results in results_by_device.items():
        csv_name = '{}-{}.csv'.format(*device_and_grade)
        with open(csv_name, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"',
                                   quoting=csv.QUOTE_MINIMAL)
            csvwriter.writerow(['ip', 'clk constraint (ps)', 'metric'] + synth_method_list)
            for ip_name, result_by_synth_method in synth_results.items():
                # Collect the available constraints across all methods and runs for this IP.
                all_constraints = sorted(
                        set(functools.reduce(operator.add,
                                         [list(result_by_synth_method[x].constraints.keys()) for x in synth_method_list])),
                        key=int)
                for constr in all_constraints:
                    for method_fetch, match_group, labels in metrics:
                        for label in labels:
                            line = [ip_name, constr, label]
                            for method in synth_method_list:
                                getter = method_fetch(result_by_synth_method[method])
                                if method in result_by_synth_method:
                                    value = getter(constr, label)
                                    line.append(
                                            value[match_group] if value else value_if_no_result)
                                else:
                                    line.append(value_if_no_result)
                            csvwriter.writerow(line)
            print('wrote {}'.format(csv_name))

    #MakePrettyGraphs(results)


if __name__ == '__main__':
    main()
