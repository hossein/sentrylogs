"""
Log file parsers provided by Sentry Logs
"""
import time

import tailhead  # same functionality as UNIX tail in python

from ..helpers import send_message

try:
    (FileNotFoundError, PermissionError)
except NameError:  # Python 2.7
    FileNotFoundError = IOError  # pylint: disable=redefined-builtin
    PermissionError = IOError  # pylint: disable=redefined-builtin


class Parser(object):  # pylint: disable=useless-object-inheritance
    """Abstract base class for any parser"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.logger = self.__doc__.strip()
        self.message = None
        self.level = None
        self.data = {
            "logger": self.logger,
        }

        self.threshold_times = 2
        self.current_times = 0
        self.lines_buffer = []

    def clear_attributes(self):
        """Reset attributes"""
        self.message = None
        self.level = None
        self.data = {
            "logger": self.logger,
        }

    def follow_tail(self):
        """
        Read (tail and follow) the log file, parse entries and send messages
        to Sentry using Raven.
        """

        try:
            follower = tailhead.follow_path(self.filepath)
        except (FileNotFoundError, PermissionError) as err:
            raise SystemExit("Error: Can't read logfile %s (%s)" %
                             (self.filepath, err))

        for line in follower:
            self.clear_attributes()

            if line is not None:
                if self.is_new_entry(line):
                    self.send_buffer()

                # Append the new entry, or append its next lines to it
                self.lines_buffer.append(line)
            else:
                if self.current_times < self.threshold_times:
                    # Check for new lines at a higher speed
                    time.sleep(1)
                    self.current_times += 1
                else:
                    # if not new lines found at self.threshold_times, send the previous message
                    self.send_buffer()
                    time.sleep(10)

    def send_buffer(self):
        """
        Parse and send the collected lines buffer if its not empty and clear it
        """
        if not self.lines_buffer:
            return

        self.parse(self.lines_buffer)

        self.current_times = 0
        self.lines_buffer = []

        send_message(
            self.message,
            self.level,
            self.data,
        )

    def is_new_entry(self, line):
        """
        Must be overridden by the subclass and return true if the line marks the start of a new entry.
        """
        raise NotImplementedError('is_new_entry() method must be implemented')

    def parse(self, line):
        """
        Parse a line of a log file.  Must be overridden by the subclass.
        The implementation must set these properties:

        - ``message`` (string)
        - ``level`` (string)

        Additional optional properties:
        - ``data`` (dict)
        """
        raise NotImplementedError('parse() method must set: '
                                  'message, level')
