#!/usr/bin/env python

import logging
import argparse
import nagiosplugin
from datetime import timedelta

_log = logging.getLogger('nagiosplugin')


class Uptime(nagiosplugin.Resource):
    def probe(self):
        _log.info('Reading system uptime from /proc/uptime')
        with open('/proc/uptime') as file:
            raw_uptime = int(float(file.readline().split(' ')[0]))
        _log.debug('Raw system uptime is %s', raw_uptime)

        yield nagiosplugin.Metric('uptime', raw_uptime, context='uptime')


class UptimeSummary(nagiosplugin.Summary):
    def ok(self, results):
        return 'uptime is %s' % str(timedelta(seconds=float(str(results['uptime'].metric))))


def main():
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('-w', '--warning', metavar='RANGE', default='', help='Return warning if uptime is outside RANGE')
    argp.add_argument('-c', '--critical', metavar='RANGE', default='',
                      help='Return critical if uptime is outside RANGE')
    argp.add_argument('-v', '--verbose', action='count', default=0,
                      help='Increase output verbosity (use up to 3 times)')
    args = argp.parse_args()

    check = nagiosplugin.Check(Uptime(), nagiosplugin.ScalarContext('uptime', args.warning, args.critical),
                               UptimeSummary())
    check.main(verbose=args.verbose)


if __name__ == '__main__':
    main()
