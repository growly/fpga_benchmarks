#!/usr/bin/python3

import argparse
import collections
import csv
import os
import re

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


class UtilizationResult:
    @staticmethod
    def Match4ColumnRow(label):
        spec = (r'^\|\s+(' + label +
                r')\s+\|\s+(\d+)?\s+\|\s+(\d+)?\s+\|\s+(\d+)?\s+\|\s+(<?\d+.\d+)?\s+\|$')
        return re.compile(spec)

    ## | CLB LUTs                   | 4455 |     0 |    203128 |  2.19 |
    #CLB_LUTS_RE = Match4ColumnRow.__func__('CLB LUTs')
    ## | Bonded IOB       |  366 |     0 |       520 | 70.38 |
    #BONDED_IOB_RE = Match4ColumnRow.__func__('Bonded IOB')

    # Match labels in the file in the order they appear here. Where there is a
    # tuple, all of the labels in the tuple are searched for on each line of
    # the file.
    LABELS= [('CLB LUTs', 'Slice LUTs', 'LUT as Logic', 'LUT as Memory',
              'LUT as Shift Register', 'Bonded IOB')]

    def __init__(self):
        # We expect to match each of these once and in the given order,
        # so that we can stop looking for one as soon as we match it, and
        # start looking for the next one. They must be in the order they appear
        # in the file.
        self.line_matchers = collections.deque()
        for label in UtilizationResult.LABELS:
            matcher = LineMatcher()
            if isinstance(label, tuple):
                for entry in label:
                    matcher.AddMatcher(
                        entry, UtilizationResult.Match4ColumnRow(entry))
            else:
                matcher.AddMatcher(
                    label, UtilizationResult.Match4ColumnRow(label))
            self.line_matchers.append(matcher)
        self.matcher = self.line_matchers.popleft()
        self.results = dict()

    def MatchNext(self, text):
        key, match = self.matcher.MatchText(text)
        if match:
            self.results[key] = match.groups()
            if self.line_matchers:
                self.matcher = self.line_matchers.popleft()


class ConstraintResult:

    def __init__(self, file_path):
        self.file_path = file_path
        self.util = None
        self.timing = None


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
        return '{}'.format(
            ', '.join([self.ip, self.synth_method, self.device, self.grade]))

    def GetUtilizationResult(self, constraint, label):
        if constraint not in self.constraints:
            print('{} missing results for constraint: {}, see {}'.format(
                repr(self), constraint, self.path))
            return None
        util = self.constraints[constraint].util
        if util is None:
            print('{} missing results for utilization, see {}'.format(
                repr(self), self.constraints[constraint].file_path))
            return None
        if label not in util.results:
            print('{} missing results for label: {}, see {}'.format(
                repr(self), label, self.constraints[constraint].file_path))
            return None
        return util.results[label]

    def ParseResults(self):
        for f in os.listdir(self.path):
            match = TEST_RESULT_FILE_RE.match(f)
            if (match):
                constraint = match.group(1)
                result_file = os.path.join(self.path, f)
                self.constraints[constraint] = ConstraintResult(result_file)

        for constraint, constraint_result in self.constraints.items():
            util = UtilizationResult()
            with open(constraint_result.file_path) as f:
                for i, line in enumerate(f):
                    util.MatchNext(line)
            constraint_result.util = util


def main():
    parser = argparse.ArgumentParser(description='Collect benchmarks results')
    parser.add_argument('--from_dir', type=str, help='Results directory')
    args = parser.parse_args()

    source_dir = None
    try:
        source_dir = os.path.realpath(args.from_dir)
    except:
        print('Could not find results in {}'.format(source_dir))

    results = []
    results_by_device = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(None)))
    for d in os.listdir(source_dir):
        match = TEST_DIR_RE.match(d)
        if match:
            result = Result(*match.groups(), os.path.join(source_dir, d))
            results.append(result)
            results_by_device[(result.device, result.grade)][result.ip][
                    result.synth_method] = result
            result.ParseResults()
        else:
            print('Could not parse result dir name: {}'.format(d))

    print('Parsed {} results'.format(len(results)))

    constr = '100'
    # index of the 'number used' tally in each output row of the Vivado results
    used = 1
    value_if_no_result = 'none'
    metrics = ['Slice LUTs', 'LUT as Logic', 'LUT as Memory', 'LUT as Shift Register',
               'Bonded IOB']
    with open('xc7a200-1.csv', 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(['ip', 'metric', 'vivado', 'yosys', 'yosys-abc9'])
        for ip_name, result_by_synth_method in results_by_device[('xc7a200', '1')].items():
            for metric in metrics:
                vivado_value = result_by_synth_method[
                        'vivado'].GetUtilizationResult(constr, metric)
                yosys_value = result_by_synth_method[
                        'yosys'].GetUtilizationResult(constr, metric)
                yosysabc9_value = result_by_synth_method[
                        'yosys-abc9'].GetUtilizationResult(constr, metric)
                line = [ip_name,
                        metric,
                        vivado_value[used] if vivado_value else value_if_no_result,
                        yosys_value[used] if yosys_value else value_if_no_result,
                        yosysabc9_value[used] if yosysabc9_value else value_if_no_result]
                csvwriter.writerow(line)


if __name__ == '__main__':
    main()
