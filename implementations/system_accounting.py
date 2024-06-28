#!/usr/bin/env python3
import argparse
import csv
import datetime
import math
import os
import struct

# see https://man.openbsd.org/OpenBSD-7.4/acct.5
# also see src/usr.bin/lastcomm/lastcomm.c 
# also see sys/kern/kern_acct.c

AHZ = 64 # granularity of data encoding in "comp_t" fields
SECSPERHOUR = 3600
SECSPERMIN = 60

ACCOUNTING_FLAGS = {
    0x001: 'fork but not exec',
    0x004: 'system call or stack mapping violation',
    0x008: 'dumped core',
    0x010: 'killed by a signal',
    0x020: 'killed due to pledge violation',
    0x040: 'memory access violation',
    0x080: 'unveil access violation',
    0x200: 'killed by syscall pin violation',
    0x400: 'BT CFI violation'
}

struct_format = '24sHHHHQIIIiII' # see https://docs.python.org/3/library/struct.html#format-characters for meaning
struct_size = struct.calcsize(struct_format)
assert struct_size == 64, f"Struct size is {struct_size}, expected 64."

def convert_comp_t(comp_t):
    converted_t = comp_t & 0x1fff  # hex 0x1fff is equivalent to octal 017777 from the referenced C code
    comp_t >>= 13
    while comp_t:
        comp_t -= 1
        converted_t <<= 3
    converted_t = converted_t / AHZ # "unit" conversion
    return converted_t 

def time_conversion(total_secs):
    hours = total_secs / SECSPERHOUR
    minutes = math.fmod(total_secs, SECSPERHOUR) / SECSPERMIN
    seconds = math.fmod(total_secs, SECSPERMIN)
    time_string = f"{hours:02.0f}:{minutes:02.0f}:{seconds:05.2f}"
    return time_string

def parse_flags(flags_value):
    set_flags = []
    for flag_bit, description in ACCOUNTING_FLAGS.items():
        if flags_value & flag_bit:
            set_flags.append(description)
    flags_string = ', '.join(set_flags)
    return flags_string

def parse_acct(file_path, process_name_encoding):
    try:
        with open(file_path, 'rb') as file: # Opening the file in binary mode
            accounting_structs = []
            pos = 1
            while True:
                # get the data from file
                encoded_data = file.read(struct_size)
                if not encoded_data:
                    break
                # decode data 
                decoded_data = struct.unpack(struct_format, encoded_data)
                command_name, user_time, system_time, elapsed_time, count_io_blocks, starting_time, user_id, group_id, avg_mem_usage, controlling_tty, process_id, flags = decoded_data
                # further decoding of values
                command_name = command_name.split(b'\x00')[0].decode(process_name_encoding)
                starting_time = datetime.datetime.utcfromtimestamp(starting_time).isoformat() + 'Z' # the value for starting_time stored with accounting is calculated from nanoboottime() (meaning the UTC timestamp that the system got booted) and the process associated value from nanouptime() at process start (meaning time elapsed since system boot) - the resulting timestamp, which we are parsing here, should be UTC based then
                user_time = time_conversion(convert_comp_t(user_time))
                system_time = time_conversion(convert_comp_t(system_time))
                elapsed_time = time_conversion(convert_comp_t(elapsed_time))
                count_io_blocks = convert_comp_t(count_io_blocks)
                flags = parse_flags(flags)
                # result
                accounting_structs.append({'index':pos, 'starting_time':starting_time, 'command_name':command_name, 'pid':process_id, 'uid':user_id, 'gid':group_id, 'tty':controlling_tty, 'user_time':user_time, 'system_time':system_time, 'elapsed_time':elapsed_time, 'average_memory_usage':avg_mem_usage, 'count_io_blocks':count_io_blocks, 'flags':flags})
                pos = pos + 1
            return accounting_structs
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
        return None

def main(file_path, csv_output, process_name_encoding):
    headers = []
    data = parse_acct(file_path, process_name_encoding)
    headers = ["index", "starting_time", "command_name", "pid", "uid", "gid", "tty", "user_time", "system_time", "elapsed_time", "average_memory_usage", "count_io_blocks", "flags"]
    if data is not None:
        if csv_output:
            with open('system_accounting.csv', 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames= headers)
                writer.writeheader()
                writer.writerows(data) 
        else:
            for element in data:
                print(element)
    else:
        print("No data to display.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', required=True, type=str, help='The path to the system accounting file.')
    parser.add_argument('-e', '--encoding', default='iso-8859-1', type=str, help='Encoding to use process names')
    parser.add_argument('--csv', default=False, action='store_true', help='output data in csv format, saved to system_accounting.csv in the current directory')
    args = parser.parse_args()
    # Check if the file exists before proceeding
    if os.path.exists(args.path):
        main(args.path, args.csv, args.encoding)
    else:
        print(f"Error: The file {args.path} does not exist or cannot be accessed.")
