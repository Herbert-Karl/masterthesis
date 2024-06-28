#!/usr/bin/env python3
import argparse
import csv
import os

SIZE_BIGRAM_SECTION = 256
OFFSET = 14

def parse_locate_database(file_path, size_of_int, byte_order, non_ascii_encoding):
    try:
        with open(file_path, 'rb') as file: # Opening the file in binary mode
            # get the data from file
            raw_bigrams = file.read(SIZE_BIGRAM_SECTION)
            encoded_data = file.read()
            # prepare decoding
            bigrams = [(raw_bigrams[i:i+2]).decode('ascii') for i in range(0, len(raw_bigrams), 2)]
            decoded_filepaths = []
            current_filepath = ""
            last_filepath = ""
            shared_prefix = 0
            index = 0
            # decoding
            while index < len(encoded_data):
                byte = encoded_data[index] # it might be called "byte", but for python, this is an "int" representing the single byte value
                if byte == 30 or (0 <= byte and byte <= 28) :
                    # we got a differential value, meaning a new file path starts
                    if current_filepath != "":
                        # check to skip a empty insertion, which is guarenteed to happen on the first loop
                        decoded_filepaths.append(current_filepath) # store file path before starting to build a new one
                    last_filepath = current_filepath
                    differential = 0
                    if byte == 30 :
                        index += 1 # step over marker
                        differential = int.from_bytes(encoded_data[index:index+size_of_int], byte_order, signed=True) - OFFSET
                        index += size_of_int
                    else :
                        differential = byte - OFFSET
                        index += 1
                    shared_prefix += differential
                    current_filepath = last_filepath[:shared_prefix]
                if byte == 31 : 
                    # got a literal value
                    literal_value = encoded_data[index+1]
                    current_filepath += literal_value.decode(non_ascii_encoding)
                    index += 2 # jump over literal value
                if 32 <= byte and byte <= 127 :
                    # got a basic ASCII printable character
                    current_filepath += chr(byte)
                    index += 1
                if 128 <= byte :
                    # got an index for a bigram
                    bigram_index = byte - 128
                    current_filepath += bigrams[bigram_index]
                    index += 1
                if byte == 29 : 
                    position = index + SIZE_BIGRAM_SECTION # add bigram bytes to index to get true byte position
                    print(f"hit undefined byte 29 at position {position} in locate database.")
                    index += 1
            decoded_filepaths.append(current_filepath) # store last file path, as the loop logic only stores them on new differential values
            return decoded_filepaths
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
        return None

def main(file_path, size_of_int, byte_order, non_ascii_encoding, csv_output):
    data = parse_locate_database(file_path, size_of_int, byte_order, non_ascii_encoding)
    if data is not None:
        if csv_output:
            with open('locate_database.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Path"])
                for element in data:
                    writer.writerow([element]) # need to encapsulate each string line in a list, as otherwise the writer would iterate the string as a list, thus writing one cell for each byte
                #writer.writerows(data)
        else:
            for element in data:
                print(element)
    else:
        print("No data to display.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', required=True, type=str, help='The path to the locate database.')
    parser.add_argument('-s', '--size', default=4, type=int, help='Size value of int for the platform that the file was taken from')
    parser.add_argument('-o', '--byte_order', choices=['little', 'big'], default='little', type=str, help='Byte order for the platform that the file was taken from')
    parser.add_argument('-e', '--encoding', default='iso-8859-1', type=str, help='Encoding to use for non-ASCII values')
    parser.add_argument('--csv', default=False, action='store_true', help='output data in csv format, saved to locate_database.csv in the current directory')
    args = parser.parse_args()
    # Check if the file exists before proceeding
    if os.path.exists(args.path):
        main(args.path, args.size, args.byte_order, args.encoding, args.csv)
    else:
        print(f"Error: The file {args.path} does not exist or cannot be accessed.")
