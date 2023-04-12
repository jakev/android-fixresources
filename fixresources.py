#!/usr/bin/env python

# DTF Core Content
# Copyright 2013-2016 Jake Valletta (@jake_valletta)
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Resolve resource values in Smali files"""
from lxml import etree
import os
import os.path
import re
import click
import logging

logging.basicConfig(level=logging.INFO)


DISPLAY_LEN = 25
PUBLIC_FILE_PATH = "/res/values/public.xml"
STRING_FILE_PATH = "/res/values/strings.xml"
SMALI_FILES_PATH = "/smali"

CONST_REGEX = re.compile("const[ \/\-].*0x[a-fA-F0-9]{4,8}$")
PACKED_SWITCH_REGEX = re.compile("\.packed-switch 0x[a-fA-F0-9]{4,8}$")

TAG = 'fixresources'


class fixresources():

    """Module class for resolving resources"""

    about = 'Resolve resource values in Smali files.'
    author = 'Jake Valletta (jakev) and Adin Drabkin (adindrabkin)'
    health = 'beta'
    name = 'fixresources'
    version = '1.0.0'

    public_dict = {}
    has_strings = False


    def do_parse_public(self, project_dir):

        """Parse public.xml file"""

        public_file_path = f"{project_dir}/{PUBLIC_FILE_PATH}"

        if not os.path.isfile(public_file_path):
            logging.error(f"'{public_file_path}' public resource file not found!")
            return -1

        logging.info("Parsing public.xml...")

        for _, element in etree.iterparse(public_file_path):
            if element.tag == "public":

                try:
                    res_id = element.attrib['id']

                    logging.debug(f"Adding new public resource value {res_id}")
                    self.public_dict[int(res_id, 16)] = [element.attrib['name'],
                                                        element.attrib['type']]

                    if element.attrib['type'] == "string":
                        self.has_strings = True

                except KeyError:
                    logging.warning("KeyError iterating public.xml, skipping!")

            # Clear the element from memory
            element.clear()

        return 0

    def do_parse_strings(self, project_dir):

        """Parse strings.xml file"""

        string_file_path = f"{project_dir}/{STRING_FILE_PATH}"

        if not os.path.isfile(string_file_path):
            logging.error(f"'{string_file_path}' public resource file not found!")
            return -1

        logging.info("Parsing strings.xml...")

        for _, element in etree.iterparse(string_file_path):

            if element.tag == "string":

                try:
                    string_name = element.attrib['name']
                    for pub in self.public_dict.keys():
                        if (self.public_dict[pub][0] == string_name and
                                        self.public_dict[pub][1] == "string"):
                            logging.debug(f"Adding string details to {string_name} (0x{pub})")
                            self.public_dict[pub].append(element.text)

                except KeyError:
                    logging.warning("KeyError iterating strings.xml, skipping!")

            # Clear the element from memory
            element.clear()

        return 0

    def do_changes(self, project_dir):

        """Do smali changes"""

        smali_files_dir = f"{project_dir}/{SMALI_FILES_PATH}"

        if not os.path.isdir(smali_files_dir):
            logging.error("Smali files directory does not exist!")
            return -2

        logging.info("Making modifications to files in smali/*...")

        for root, dirs, files in os.walk(smali_files_dir):

            for filename in files:
                file_path = os.path.join(root, filename)

                # Smali only files and no R.smali junk
                if (re.search(".*\.smali$", file_path)
                                    and file_path != 'R.smali'):

                    self.change_file(file_path)

    def change_file(self, file_path):

        """Perform change to a smali file"""

        data = ''
        file_modded = False

        for line in re.split("\n", open(file_path).read()):

            # First do "const-string" instances
            if re.search(CONST_REGEX, line):

                # Get the actual value
                res_value = line[line.find(",") + 2:len(line)]

                # To save space, some are const/high16
                if line.find("high16") != -1:
                    res_value_int = int(res_value + "0000", 16)
                else:
                    res_value_int = int(res_value, 16)

                # Determine if this is a value in our list
                if res_value_int in self.public_dict.keys():
                    logging.debug(f"We found a resource identifier: res_value [file_path]")
                                                   

                    line_len = len(line)
                    line += (f"\t#Public value '{self.public_dict[res_value_int][0]}' (type={self.public_dict[res_value_int][1]})")

                    if len(self.public_dict[res_value_int]) == 3:
                        string_value = self.public_dict[res_value_int][2]

                        if string_value is None:
                            logging.warn(f"String value for value {res_value} not found!")
                            continue

                        formatted_string_value = (string_value[0:DISPLAY_LEN]
                                + ("..." if len(string_value) > DISPLAY_LEN
                                        else ""))


                        line += (f"\n{' ' * line_len}\t#{self.public_dict[res_value_int][0]} = '{formatted_string_value}'")

                    file_modded = True

            # Now check for "packed-switch" instances
            elif re.search(PACKED_SWITCH_REGEX, line):

                res_value = line[line.find("0x"): len(line)]
                res_value_int = int(res_value, 16)

                # Determine if this is a value in our list
                if res_value_int in self.public_dict.keys():
                    logging.debug(f"Found packed-switch resource identifier: {res_value}")


                    line += f"\t#Public value '{self.public_dict[res_value_int][0]}' (type={self.public_dict[res_value_int][1]})"

                    file_modded = True

            # Add the new data to a buffer
            data += line + "\n"

        # Write the changes out.
        if file_modded == True:
            output = open(file_path, 'w')
            output.write(data)
            logging.debug(f"Changes applied to file '{file_path}'")
            output.close()
        else:
            logging.debug(f"No changes to file '{file_path}'")

        return 0

    def do_fix(self, decoded_app_dir):

        """Do fix resources"""

        arg_app_dir = decoded_app_dir

        if not os.path.isdir(arg_app_dir):
            logging.error(f"Application directory '{arg_app_dir}' doesnt exist!")
            return -1

        self.has_strings = False
        self.public_dict = {}

        # First do the public resources
        if self.do_parse_public(arg_app_dir) != 0:
            return -2

        # Next do strings
        if self.has_strings:
            if self.do_parse_strings(arg_app_dir) != 0:
                return -3

        # Do actual changes
        if self.do_changes(arg_app_dir) != 0:
            return -4

        logging.info("Process complete!")


    def execute(self, decoded_app_dir):

        """Main class execution"""

        return self.do_fix(decoded_app_dir)

@click.command()
@click.argument("decoded_app_dir", type=click.Path(exists=True))
def main(decoded_app_dir):
    """
    Usage: fixresources [decoded_app_dir]
    """

    _fixresources = fixresources()
    _fixresources.execute(decoded_app_dir) 


if __name__ == '__main__':
    main()