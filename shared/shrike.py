#!/usr/bin/env python
# SnapServ/monitoring-plugins - Simple and reliable Nagios / Icinga plugins
# Copyright (C) 2016 - 2017 SnapServ Mathis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# ==================== BEGIN OF NOTICE ====================
# This library might be moved into a separate pip package one day, if further features should be
# added. It currently only supports connecting to the BIRD control socket, executing various
# commands without parsing their output and fetching statistics for one or all protocols.
# ===================== END OF NOTICE =====================

import re
import socket
from enum import Enum


class ShrikeException(Exception):
    pass


class ShrikeBirdException(ShrikeException):
    pass


class ShrikeSocketException(ShrikeException):
    pass


class ShrikeBufferedSocket:
    def __init__(self, socket_path):
        self._socket = None
        self._socket_path = socket_path
        self._buffer = b''
        self._connect_socket()

    def _connect_socket(self):
        try:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(self._socket_path)
        except Exception as e:
            raise ShrikeSocketException('Could not connect to BIRD UNIX socket: %s'
                                        % self._socket_path)

    def read_socket(self, max_bytes=1024, expect_additional_data=True):
        previous_buffer_length = len(self._buffer)
        self._buffer += self._socket.recv(max_bytes)

        if expect_additional_data and len(self._buffer) == previous_buffer_length:
            raise ShrikeSocketException('Could not read additional data from BIRD UNIX socket. '
                                        + 'Failed after %d bytes.' % previous_buffer_length)

    def write_socket(self, data):
        self._socket.send(bytes(data, 'utf-8'))

    @property
    def buffer(self):
        return str(self._buffer, 'utf-8')

    @buffer.setter
    def buffer(self, data):
        self._buffer = bytes(data, 'utf-8')


class ShrikeQueryResultCode(Enum):
    WELCOME = '0001'
    TABLE_ENTRY_PROTOCOL_LIST = '1002'
    TABLE_ENTRY_PROTOCOL_DETAIL = '1006'
    TABLE_HEADING = '2'  # Actually 2XXX, but has to be compared with .startswith()


class ShrikeQuery:
    QUERY_RESULT_LINE_DELIMITER = '\n'
    QUERY_RESULT_LINE_REGEX = re.compile('^(?P<code>[0-9]{4})(?P<type>(?: |-))(?P<data>.*)')
    QUERY_RESULT_LAST_LINE_REGEX = re.compile('^[0-9]{4} ')

    QUERY_RESULT_CODE_ERROR_MAPPINGS = {
        '8000': 'Reply too long',
        '8001': 'Route not found',
        '8002': 'Configuration file error',
        '8003': 'No protocols match',
        '8004': 'Stopped due to reconfiguration',
        '8005': 'Protocol is down => cannot dump',
        '8006': 'Reload failed',
        '8007': 'Access denied',
        '8008': 'Evaluation runtime error',
        '9000': 'Command too long',
        '9001': 'Parse error',
        '9002': 'Invalid symbol type'
    }

    def __init__(self, query):
        self._query = query

    def execute(self, socket_):
        socket_.write_socket(self._query + '\n')
        return ShrikeQuery.parse_result(socket_)

    @staticmethod
    def parse_result(socket_):
        raw_result = ShrikeQuery._fetch_raw_result(socket_)
        result_lines = ShrikeQuery._parse_raw_result(raw_result)
        results = []

        for result_line in result_lines:
            # If the result line code maps to a known error, raise a ShrikeBirdException
            if result_line['code'] in ShrikeQuery.QUERY_RESULT_CODE_ERROR_MAPPINGS:
                raise ShrikeBirdException(
                    ShrikeQuery.QUERY_RESULT_CODE_ERROR_MAPPINGS[result_line['code']])

            # Add the line in all other cases to the results array, including its code to simplify
            # further parsing, e.g. stripping out headers.
            results.append(result_line)

        return results

    @staticmethod
    def _fetch_raw_result(socket_):
        line_buffer = []

        while True:
            # Try to read up to 1024 bytes of additional data by using ShrikeBufferedSocket, which
            # throws an ShrikeSocketException if no additional data could be read.
            socket_.read_socket(1024)

            # Check if the socket buffer contains line delimiters and if so, process each line, add
            # the results to the line buffer and remove the processed lines from the socket buffer.
            if socket_.buffer.find(ShrikeQuery.QUERY_RESULT_LINE_DELIMITER):
                lines = socket_.buffer.split(ShrikeQuery.QUERY_RESULT_LINE_DELIMITER)
                new_socket_buffer = lines.pop(-1)

                while len(lines) > 0:
                    line = lines.pop(0)
                    line_buffer.append(line)

                    # If a line is not marked as continuation, return all lines including the last
                    # one up to that certain point. Additionally, all the lines which were not
                    # related to this command should be added back to the socket buffer, so that
                    # they can be reprocessed by the next command.
                    if ShrikeQuery.QUERY_RESULT_LAST_LINE_REGEX.match(line_buffer[-1]):
                        socket_.buffer = ShrikeQuery.QUERY_RESULT_LINE_DELIMITER.join(lines) \
                                         + new_socket_buffer
                        return line_buffer

                # We have not reached the end of out output yet, so keep the processed lines and
                # flush the buffer by removing all data except the last line for further processing.
                socket_.buffer = new_socket_buffer

    @staticmethod
    def _parse_raw_result(raw_result):
        result_lines = []
        previous_line = None

        for raw_result_line in raw_result:
            # Skip empty lines to avoid errors in processing.
            if len(raw_result_line) == 0:
                continue

            # Parse the current line, pass in the previous line for short-continuations (using
            # solely a space to use the same status as the line above) and save the parsed line
            # as the previous line afterwards.
            current_line = ShrikeQuery._parse_raw_result_line(raw_result_line, previous_line)
            result_lines.append(current_line)
            previous_line = current_line

        return result_lines

    @staticmethod
    def _parse_raw_result_line(raw_result_line, previous_line):
        # If the line starts with a space, reuse the code of the previous line, add the data of
        # the current line to it and return it as the result.
        if raw_result_line.startswith(' '):
            return dict(code=previous_line['code'], data=raw_result_line[1:])

        # Try to match the line against the BIRD query result line regular expression and raise an
        # Exception if the regex does not return any matches.
        match = re.match(ShrikeQuery.QUERY_RESULT_LINE_REGEX, raw_result_line)
        if not match:
            raise ShrikeSocketException('Received invalid result line on BIRD UNIX socket. Could '
                                        + 'not parse the following line: %s' % raw_result_line)

        # Return a dictionary telling the line code and data
        return dict(code=match.group('code'), data=match.group('data'))


class ShrikeProtocolDetailParser:
    RE_PREFERENCE = re.compile('^\s*Preference:\s+(?P<value>\d+)$')
    RE_IMPORT_LIMIT = re.compile('^\s*Import limit:\s+(?P<value>\d+)$')
    RE_RECEIVE_LIMIT = re.compile('^\s*Receive limit:\s+(?P<value>\d+)$')
    RE_EXPORT_LIMIT = re.compile('^\s*Export limit:\s+(?P<value>\d+)$')
    RE_LAST_ERROR = re.compile('^\s*Last error:\s+(?P<value>.+)$')
    RE_ROUTE_STATS = re.compile('^\s*Routes:\s+(?P<imported>\d+) imported, (?:(?P<filtered>\d+) '
                                + 'filtered, )?(?P<exported>\d+) exported, (?P<preferred>\d+) '
                                + 'preferred$')
    RE_ROUTE_CHANGE_STATS = re.compile('^\s*(?P<type>(?:Import|Export) (?:updates|withdraws)):\s+'
                                       + '(?:(?P<received>\d+)|---)\s+(?:(?P<rejected>\d+)|---)'
                                       + '\s+(?:(?P<filtered>\d+)|---)\s+(?:(?P<ignored>\d+)|---)'
                                       + '\s+(?:(?P<accepted>\d+)|---)$')

    RE_BGP_SOURCE_ADDRESS = re.compile('^\s*Source address:\s+(?P<value>\S+)$')
    RE_BGP_STATE = re.compile('^\s*BGP state:\s+(?P<value>\S+)$')
    RE_BGP_NEIGHBOR_ADDRESS = re.compile('^\s*Neighbor address:\s+(?P<value>\S+)$')
    RE_BGP_NEIGHBOR_AS = re.compile('^\s*Neighbor AS:\s+(?P<value>\d+)$')
    RE_BGP_NEIGHBOR_ID = re.compile('^\s*Neighbor ID:\s+(?P<value>\S+)$')
    RE_BGP_NEIGHBOR_CAPS = re.compile('^\s*Neighbor caps:\s+(?P<value>.+)$')

    @staticmethod
    def parse(result_line):
        # Define all parser functions which should be called to parse potential results
        parser_mappings = {
            'preference': ShrikeProtocolDetailParser._preference,
            'import_limit': ShrikeProtocolDetailParser._import_limit,
            'receive_limit': ShrikeProtocolDetailParser._receive_limit,
            'export_limit': ShrikeProtocolDetailParser._export_limit,
            'last_error': ShrikeProtocolDetailParser._last_error,

            'route_stats': ShrikeProtocolDetailParser._route_stats,
            'route_change_stats': ShrikeProtocolDetailParser._route_change_stats,

            'bgp_state': ShrikeProtocolDetailParser._bgp_state,
            'bgp_source_address': ShrikeProtocolDetailParser._bgp_source_address,
            'bgp_neighbor_address': ShrikeProtocolDetailParser._bgp_neighbor_address,
            'bgp_neighbor_as': ShrikeProtocolDetailParser._bgp_neighbor_as,
            'bgp_neighbor_id': ShrikeProtocolDetailParser._bgp_neighbor_id,
            'bgp_neighbor_caps': ShrikeProtocolDetailParser._bgp_neighbor_caps
        }

        # Loop through all parser functions and immediately return if a match is found
        for parser_name, parser_function in parser_mappings.items():
            parser_result = parser_function(result_line)
            if parser_result:
                return [parser_name, parser_result]

        return None

    @staticmethod
    def _preference(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_PREFERENCE, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _import_limit(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_IMPORT_LIMIT, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _receive_limit(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_RECEIVE_LIMIT, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _export_limit(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_EXPORT_LIMIT, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _last_error(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_LAST_ERROR, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _route_stats(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_ROUTE_STATS, result_line)
        if match:
            return {
                'imported': match.group('imported'),
                'exported': match.group('exported'),
                'preferred': match.group('preferred'),
                'filtered': match.group('filtered')
            }
        else:
            return None

    @staticmethod
    def _route_change_stats(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_ROUTE_CHANGE_STATS, result_line)
        if match:
            type_ = match.group('type').lower().replace(' ', '_')
            return {
                type_: {
                    'received': match.group('received') or 0,
                    'rejected': match.group('rejected') or 0,
                    'filtered': match.group('filtered') or 0,
                    'ignored': match.group('ignored') or 0,
                    'accepted': match.group('accepted') or 0
                }
            }
        else:
            return None

    @staticmethod
    def _bgp_source_address(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_BGP_SOURCE_ADDRESS, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _bgp_state(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_BGP_STATE, result_line)
        return match.group('value').lower() if match else None

    @staticmethod
    def _bgp_neighbor_address(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_BGP_NEIGHBOR_ADDRESS, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _bgp_neighbor_as(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_BGP_NEIGHBOR_AS, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _bgp_neighbor_id(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_BGP_NEIGHBOR_ID, result_line)
        return match.group('value') if match else None

    @staticmethod
    def _bgp_neighbor_caps(result_line):
        match = re.match(ShrikeProtocolDetailParser.RE_BGP_NEIGHBOR_CAPS, result_line)
        return match.group('value').lower() if match else None


class Shrike:
    def __init__(self, socket_path):
        self._socket = None
        self._socket_path = socket_path
        self._connect()

    def _connect(self):
        self._socket = ShrikeBufferedSocket(self._socket_path)

        # Check if the newly connected socket received a proper welcome message
        results = ShrikeQuery.parse_result(self._socket)
        if len(results) != 1 or results[0]['code'] != ShrikeQueryResultCode.WELCOME.value:
            raise ShrikeBirdException('Expected WELCOME message on BIRD UNIX socket after '
                                      + 'connecting, received unexpected data: ', results)

    def execute(self, query_string):
        return ShrikeQuery(query_string).execute(self._socket)

    def get_protocol(self, protocol_name):
        columns = None
        protocol = None
        protocols = {}

        # If no protocol name was given, collect data for all protocols. There is also an alias /
        # helper function called 'get_protocols', which will just call this function without
        # specifying a name. This helps us avoiding duplicate code.
        if protocol_name is not None:
            result_lines = self.execute('show protocols all %s' % protocol_name)
        else:
            result_lines = self.execute('show protocols all')

        # Try to process and parse each line, if their order and values match our expected scheme.
        for result_line in result_lines:
            # Check if the current result line code equals to a table heading - if that is the case,
            # store the given columns for further usage.
            if result_line['code'].startswith(ShrikeQueryResultCode.TABLE_HEADING.value):
                columns = result_line['data'].split()
                protocol = None

            # If the result line code is a table entry of the protocol list, zip the values of the
            # line with the previously parsed columns into a dictionary.
            elif result_line['code'] == ShrikeQueryResultCode.TABLE_ENTRY_PROTOCOL_LIST.value:
                if columns is None:
                    raise ShrikeBirdException('Expected TABLE HEADING message on BIRD UNIX socket '
                                              + 'before receiving table entries, can not continue.')

                protocol = dict(zip(columns, result_line['data'].split()))
                protocols[protocol['name']] = protocol

            elif result_line['code'] == ShrikeQueryResultCode.TABLE_ENTRY_PROTOCOL_DETAIL.value:
                if protocol is None:
                    raise ShrikeBirdException('Expected TABLE ENTRY PROTOCOL LIST message on BIRD '
                                              + 'unix socket before receiving TABLE ENTRY PROTOCOL '
                                              + 'DETAIL message, can not continue.')

                # Send the result line containing protocol details to a dedicated parser, which will
                # either return 'None' if nothing could be parsed or a key/value mapping for setting
                # or merging with the current protocol data dictionary.
                parser_result = ShrikeProtocolDetailParser.parse(result_line['data'])
                if parser_result is not None:
                    if parser_result[0] in protocol \
                            and isinstance(protocol[parser_result[0]], dict):
                        protocol[parser_result[0]].update(parser_result[1])
                    else:
                        protocol[parser_result[0]] = parser_result[1]

        return protocols

    def get_protocols(self):
        return self.get_protocol(None)
