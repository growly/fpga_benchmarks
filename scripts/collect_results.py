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
    SLACK_MET_OR_NOT_LABEL = 1
    CRITICAL_PATH_SLACK_LABEL = 2

    @staticmethod
    def MatchSlackMetOrNot():
        spec = (r'^Slack \(([A-Z]+)\).*$')
        return re.compile(spec)

    def MatchCriticalPathSlack():
        spec = (r'^\s+slack\s+(-?\d+\.\d+)\s+$')
        return re.compile(spec)

    def __init__(self):
        LABELS = {
            TimingResult.SLACK_MET_OR_NOT_LABEL:
                TimingResult.MatchSlackMetOrNot(),
            TimingResult.CRITICAL_PATH_SLACK_LABEL:
                TimingResult.MatchCriticalPathSlack()
        }

        super().__init__(LABELS, lambda x: LABELS[x])


class ClockConstraintResult:

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
        # This should be a dict of constraint: ClockConstraintResult
        self.constraints = dict()
    
    def __repr__(self):
        return '({}-{}) {}, {} '.format(
            self.device, self.grade, self.ip, self.synth_method)

    def GetClockConstraintResult(self, constraint):
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
            constr = self.GetClockConstraintResult(constraint)
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
            constr = self.GetClockConstraintResult(constraint)
            if constr.util is None:
                raise ValueError('missing results for utilisation'.format(
                    repr(self)))
            return constr.util.GetLabel(label)
        except ValueError as err:
            print('{} {}, see {}'.format(
                repr(self), err, self.path), file=sys.stderr)
            return None

    def MetTimingAt(self, constr):
        """Whether the results show that timing was met at the given constraint."""
        result = self.GetTimingResult(
            constr, TimingResult.SLACK_MET_OR_NOT_LABEL)
        if result is None:
            return False
        return result[0] == 'MET'

    def GetTimingResult(self, constraint, label):
        try:
            constr = self.GetClockConstraintResult(constraint)
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
                self.constraints[constraint] = ClockConstraintResult(result_file)

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


def GraphMetricAcrossConstraints(synth_results, label, ip_name):
    results_by_synth_method = synth_results[ip_name]
    synth_methods = sorted(list(results_by_synth_method.keys()))

    all_valid_results = dict()
    for method in synth_methods:
        # Extract constraints and parameter if valid.
        valid_results = dict()
        method_results = results_by_synth_method[method]
        for clk in method_results.constraints.keys():
            if method_results.MetTimingAt(clk):
                result = method_results.GetUtilizationResult(clk, label)[1]
                valid_results[int(clk)] = int(result)
        all_valid_results[method] = valid_results

    # Now generate a plot of one line per method.
    fig, ax = plt.subplots()

    for method, results in all_valid_results.items():
        data = sorted(results.items(), key=lambda x: x[0])
        clks, values = zip(*data)
        ax.plot(clks, values, label=method)

    ax.set(title='{} vs clock for "{}"'.format(label, ip_name),
           ylabel=label,
           xlabel='clock constraint (ps)')
    ax.legend()
    plt.show()


def MakePrettyGraph(synth_results, label, ip_names=None, normalise=True):
    # This could automatically filter results by designs with non-zero results.
    ip_names = ip_names or list(synth_results.keys())

    y_by_method = collections.defaultdict(list)

    synth_methods_set = set()
    # Find all the methods used over all results for all designs:
    for ip_name, result_by_synth_method in synth_results.items():
        synth_methods_set.update(result_by_synth_method.keys())
    synth_methods = sorted(list(synth_methods_set))

    acting_constraints = []

    # Fill in the values achieved by each design under each method for the
    # given label:
    for ip_name in ip_names:
        result_by_synth_method = synth_results[ip_name]

        all_constraints = list(
                map(int, FindAllClockConstraintsAcrossAllMethods(result_by_synth_method)))
        # Ok, attempt to find the best constraint for which all methods pass.
        best_constraint = max(all_constraints)

        for clk in all_constraints:
            meets = [result_by_synth_method[method].MetTimingAt(str(clk))
                    if method in result_by_synth_method else False
                    for method in synth_methods]
            if all(meets) and clk < best_constraint:
                best_constraint = clk
            #for method in synth_methods:
            #    if result_by_synth_method[method].MetTimingAt(str(clk)):
            #        print('{} {} met @ {} ps'.format(ip_name, method, clk))
        acting_constraints.append(best_constraint)
        #print('{} best clk: {}'.format(ip_name, best_constraint))

        value_by_method = dict()

        for method in synth_methods:
            if method not in result_by_synth_method:
                print('{}: {} has no results'.format(ip_name, method))
                value_by_method[method] = 0
                continue
            value = result_by_synth_method[method].GetUtilizationResult(str(best_constraint), label)
            if value is None:
                print('{}: {}/{} has no results'.format(ip_name, method, label))
                value_by_method[method] = 0
                continue
            # Extract the appropriate match group.
            value = value[1]
            try:
                value_by_method[method] = int(value)
            except ValueError as e:
                print(e, file=sys.stderr)
                value_by_method[method] = 0
                continue
        for key, value in value_by_method.items():
            y_by_method[key].append(value)

    if not synth_methods:
        print("Cannot generate graphs (label={}): no synth methods found.".format(label))
        return

    def autolabel(rects):
        for rect in rects:
            ax.annotate('@ {}ps'.format(acting_constraints[i]),
                xy=(rect.get_x() + rect.get_width()/2, rect.get_height()),
                xytext=(0, 3),
                textcoords='offset points',
                ha='center', va='bottom')

    x = np.arange(len(ip_names))
    fig, ax = plt.subplots()
    num_bars = len(synth_methods)
    width = (1.0 - 0.2)/num_bars
    for i in range(num_bars):
        # You specify the centre of the bars on the x axis as the first argument.
        rects = ax.bar(x - (num_bars - 1)*width/2 + i*width,
                       y_by_method[synth_methods[i]],
                       width,
                       label=synth_methods[i])

        y_labels = map(lambda x: '{}\n@ {:.2f} ns'.format(x[0], x[1]/1000.0), zip(ip_names, acting_constraints))

    ax.set_xlabel('designs')
    ax.set_xticks(x)
    ax.set_xticklabels(y_labels, rotation='vertical')
    #plt.xticks(rotation=45)
    ax.set_ylabel(label)
    ax.legend()
    ax.set_title('{} vs designs'.format(label))

    fig.tight_layout()
    plt.show()


def FindAllClockConstraintsAcrossAllMethods(result_by_synth_method):
    # Collect the available constraints across all methods and runs for this IP.
    if not result_by_synth_method:
        return []
    return sorted(
        # Flatten the list of lists and de-duplicate elements through a set.
        set(functools.reduce(
            operator.add,
            # The following a list of a list of every key in the constraints dicts.
            [list(
                result_by_synth_method[x].constraints.keys())
             for x in result_by_synth_method.keys()])),
        # Impose natural number ordering on the values, even though they're strings.
        key=int)


def DumpAllAsCSV(results_by_device, synth_methods, metrics):
    value_if_no_result = 'none'
    synth_method_list = sorted(synth_methods)
    for device_and_grade, synth_results in results_by_device.items():
        csv_name = '{}-{}.csv'.format(*device_and_grade)
        with open(csv_name, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"',
                                   quoting=csv.QUOTE_MINIMAL)
            csvwriter.writerow(['ip', 'clk constraint (ps)', 'metric'] + synth_method_list)
            for ip_name, result_by_synth_method in synth_results.items():
                all_constraints = FindAllClockConstraintsAcrossAllMethods(result_by_synth_method)
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
    for entry in os.scandir(source_dir):
        if not entry.is_dir(follow_symlinks=True):
            # Skip non-directories.
            continue
        match = TEST_DIR_RE.match(entry.name)
        if match:
            result = Result(*match.groups(), os.path.join(entry.path))
            results.append(result)
            results_by_device[(result.device, result.grade)][result.ip][
                    result.synth_method] = result
            synth_methods.add(result.synth_method)
            ips.add(result.ip)
            result.ParseResults()
        else:
            print('Could not parse result dir name: {}'.format(entry.name))

    print('Scanned {} result files'.format(len(results)))
    print('Found {} IP(s); {} synth method(s)'.format(
        len(ips), len(synth_methods)))

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
    #DumpAllAsCSV(results_by_device, synth_methods, metrics

    ip_names = ['stereovision0', 'bgm', 'blob_merge', 'LU32PEEng', 'LU8PEEng',
            'boundtop', 'sha', 'LU64PEEng', 'arm_core', 'stereovision2']
    #MakePrettyGraph(results_by_device[('xc7a200', '1')],
    #                'Slice LUTs',
    #                ip_names)
    #MakePrettyGraph(results_by_device[('xc7a200', '1')],
    #                'Slice LUTs',
    #                None)

    for ip in ip_names:
        GraphMetricAcrossConstraints(results_by_device[('xc7a200', '1')],
                                     'Slice LUTs',
                                     ip)


if __name__ == '__main__':
    main()
