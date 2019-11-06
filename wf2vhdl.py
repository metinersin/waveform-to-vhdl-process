# add docstring

import argparse
import re


def add_str_head_of_lines_dest(dest, s):
    lines = dest.split('\n')
    lines = map(lambda line: s + line, lines)
    lines = '\n'.join(lines)
    lines = lines + '\n'
    return lines


parser = argparse.ArgumentParser(description='Convert a special waveform comment in a vhdl file to process statements.')
parser.add_argument('path', help='Path to the VHDL testbench file containing special comments.')
parser.add_argument('-v', '--verbose', action='store_true', help='Display debug messages')
args = parser.parse_args()

path = args.path
verbose = args.verbose

time_units = 'fs|ns|ps|ms'
reserved_word = 'UNIT'
magic_flag = r'--\*--'
reserved_word = 'UNIT'
clock_signal_name = 'clk'
clock_period_name = 'CLKPER'
process_name = 'process'
file_name_tail = '.wf2'
starting_line = -1
ending_line = -1
first_comment = tuple()
unit_time = tuple()
clock = tuple()
signals = {}

lines = []
process_code = []
with open(path, 'r') as f:
    lines = f.readlines()


for i, line in enumerate(lines):
    if re.match(r'\s*{0:}'.format(magic_flag), line):
        if starting_line == -1:
            starting_line = i
            continue

        ending_line = i
        break
else:
    raise Exception('{0:} does not contain special comments.'.format(path))

if ending_line - starting_line < 3:
    raise Exception('{0:} needs to have at least 2 lines inside special flags. You give {1:}'.format(path, ending_line - starting_line - 1))

if verbose:
    print('Starting line = {0:}, ending line = {1:}'.format(starting_line, ending_line))

m = re.match(r'\s*--\s*([_a-zA-z][0-9a-zA-z_]*)\s*(\d+(?:\.\d+)?)\s*({0:})'.format(time_units), lines[starting_line + 1])
if not m:
    raise Exception('The format of the first special comment is not correct! Format is [{0:} or other] number [{1:}]'.format(reserved_word, time_units))
first_comment = (m.group(1), int(m.group(2)), m.group(3))

if verbose:
    print('First comment = {0:}'.format(first_comment))


for i, line in enumerate(lines[starting_line + 2:ending_line]):
    m = re.match(r'\s*--\s*([_a-zA-z][0-9a-zA-z_]*)\s*([01]+)', line)
    if not m:
        raise Exception('At file {0:}, at line {1:}: The signal format is wrong!. Example format is signal_name(compatible with VHDL naming) 001010110...'.format(path, i + starting_line + 3))

    signals[m.group(1)] = m.group(2)

    if verbose:
        print('Signal #{0:}: {1:} {2:}'.format(i + 1, m.group(1), m.group(2)))

if first_comment[0] == reserved_word:
    unit_time = (first_comment[1], first_comment[2])

    if clock_signal_name in signals.keys():
        m = re.match(r'(([01])\2*)', signals[clock_signal_name])
        hp = m.group(1)
        if verbose:
            print('Clock signal: {0:}\nHalf period of clock signal: {1:}'.format(signals[clock_signal_name], hp))

        clock = (clock_period_name, len(hp) * 2 * unit_time[0], unit_time[1])
        del signals[clock_signal_name]
else:
    if not clock_signal_name in signals.keys():
        raise Exception('If the first comment is not {0:} then there must be a signal named {1:}!'.format(reserved_word, clock_signal_name))

    m = re.match(r'(([01])\2*)', signals[clock_signal_name])
    hp = m.group(1)
    if verbose:
        print('Clock signal: {0:}\nHalf period of clock signal: {1:}'.format(signals[clock_signal_name], hp))

    clock = (first_comment[0], first_comment[1], first_comment[2], hp)
    unit_time = (clock[1] / 2 / len(hp), clock[2])
    del signals[clock_signal_name]

if verbose:
    print('unit_time = {0:}\nclock = {1:}'.format(unit_time, clock))


if len(clock) != 0:
    process_code.append('-- CONSTANT {0:}: TIME := {1:} {2:};\n'.format(*clock[:-1]))
    if verbose:
        print('Process code: {0:}'.format(repr(process_code[-1])))
        print(process_code[-1])


    process_code.append("{0:}_{1:}: PROCESS\nBEGIN\n\t{0:} <= '{2:}';\n\tWAIT FOR {3:} / 2;\n\t{0:} <= '{4:}';\n\tWAIT FOR {3:} / 2;\nEND PROCESS;\n".format(clock_signal_name, process_name, clock[3][0], clock[0], '1' if clock[3][0] == '0' else '0'))
    if verbose:
        print('Process code: {0:}'.format(repr(process_code[-1])))
        print(process_code[-1])


for signal_name in signals:
    s = '{0:}_{1:}: PROCESS\nBEGIN\n'.format(signal_name, process_name)
    for bit in signals[signal_name]:
        s += "\t{0:} <= '{1:}';\n\tWAIT FOR {2:} {3:};\n".format(signal_name, bit, unit_time[0], unit_time[1])
    s += 'END PROCESS;\n'
    process_code.append(s)
    if verbose:
        print('Process code for signal {0:}: {1:}'.format(signal_name, repr(process_code[-1])))
        print(process_code[-1])

m = re.match(r'(.*){0:}'.format(magic_flag), lines[starting_line])
heading = m.group(1)
if verbose:
    print('Heading = {0:}'.format(heading))

process_code = list(map(lambda code: add_str_head_of_lines_dest(code, heading), process_code))
final_code = ''.join(process_code)
if verbose:
    print('Final code:\n{0:}'.format(final_code))

m = re.search(r'.vhdl$', path)
_path = path + file_name_tail if not m else path[:m.span()[0]] + file_name_tail + '.vhdl'

with open(_path, 'w') as f:
    f.write(''.join(lines[:ending_line + 1]) + final_code + ''.join(lines[ending_line + 1:]))
