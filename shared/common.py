# SnapServ/monitoring-plugins - Simple and reliable Nagios / Icinga plugins
# Copyright (C) 2016 SnapServ - Pascal Mathis
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

import abc
import copy
import argparse
import nagiosplugin

from typing import Any, Dict, Tuple


class NagiosPlugin(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.check = None  # type: nagiosplugin.Check
        self.argument_parser = None  # type: argparse.ArgumentParser
        self.arguments = {}  # type: Dict[str, Any]
        self.keyword_arguments = {}  # type: Dict[str, Any]
        self.exclude_from_kwargs = ()  # type: Tuple[str]

        self._initialize_argument_parser()

    @abc.abstractmethod
    def declare_arguments(self):
        pass

    @abc.abstractmethod
    def instantiate_check(self):
        return

    @nagiosplugin.guarded()
    def execute(self):
        self.declare_arguments()
        self.parse_arguments()
        self.instantiate_check()

        if self.check:
            self.check.main(verbose=self.arguments.get('verbose', 0))
        else:
            raise RuntimeError(
                'NagiosPlugin[%s] did not instantiate object of type nagiosplugin.Check()' % self.__class__.__name__)

    def parse_arguments(self):
        self.arguments = vars(self.argument_parser.parse_args())
        self.keyword_arguments = copy.deepcopy(self.arguments)
        [self.keyword_arguments.pop(argument) for argument in self.exclude_from_kwargs]

    def _initialize_argument_parser(self):
        self.argument_parser = argparse.ArgumentParser(description=__doc__)
        self.argument_parser.add_argument('-v', '--verbose', action='count', default=0,
                                          help='Increase output verbosity, can be used up to 3 times.')
        self.exclude_from_kwargs += ('verbose',)


class CommaSeparatedSummary(nagiosplugin.Summary):
    def ok(self, results):
        return ', '.join([str(result) for result in results if result.metric])


class ExceptionContext(nagiosplugin.Context):
    def __init__(self, name='exception'):
        super(ExceptionContext, self).__init__(name)

    def evaluate(self, metric, resource):
        return self.result_cls(nagiosplugin.Critical, str(metric.value), metric)


class DaysValidContext(nagiosplugin.Context):
    fmt_hint = 'less than {value} days'

    def __init__(self, name, check_lifetime=True, warning_days=0, critical_days=0, fmt_metric='Valid for {value} days'):
        super(DaysValidContext, self).__init__(name, fmt_metric=fmt_metric)

        self.name = name
        self.check_lifetime = check_lifetime
        self.warning_days = warning_days
        self.critical_days = critical_days

        self.warning = nagiosplugin.Range('@%d:' % self.warning_days)
        self.critical = nagiosplugin.Range('@%d:' % self.critical_days)

    def evaluate(self, metric, resource):
        if self.check_lifetime and metric.value is not None:
            if self.critical.match(metric.value):
                return nagiosplugin.Result(nagiosplugin.Critical, hint=self.fmt_hint.format(value=self.critical_days),
                                           metric=metric)
            elif self.warning.match(metric.value):
                return nagiosplugin.Result(nagiosplugin.Warn, hint=self.fmt_hint.format(value=self.warning_days),
                                           metric=metric)
            else:
                return super(DaysValidContext, self).evaluate(metric, resource)
        else:
            return nagiosplugin.Result(nagiosplugin.Ok)

    def performance(self, metric, resource):
        if self.check_lifetime and metric.value is not None:
            return nagiosplugin.Performance(self.name, metric.value, '')
        return None
