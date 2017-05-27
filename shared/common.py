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

import copy
import argparse
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Optional  # pylint: disable=unused-import

import nagiosplugin


class NagiosPlugin(ABC):
    def __init__(self) -> None:
        self.check = None  # type: nagiosplugin.Check
        self.argument_parser = None  # type: argparse.ArgumentParser
        self.arguments = {}  # type: Dict[str, Any]
        self.keyword_arguments = {}  # type: Dict[str, Any]
        self.exclude_from_kwargs = ()  # type: Tuple

        self._initialize_argument_parser()

    @abstractmethod
    def declare_arguments(self) -> None:
        pass

    @abstractmethod
    def instantiate_check(self) -> nagiosplugin.Check:
        pass

    @nagiosplugin.guarded()
    def execute(self) -> None:
        self.declare_arguments()
        self.parse_arguments()
        self.check = self.instantiate_check()

        if self.check:
            self.check.main(verbose=self.arguments.get('verbose', 0))
        else:
            raise RuntimeError(
                'NagiosPlugin[%s] did not instantiate object of type nagiosplugin.Check()'
                % self.__class__.__name__
            )

    def parse_arguments(self) -> None:
        # Parse all arguments and convert them to keyword arguments, excluding specific
        # 'keys' / 'keywords'
        self.arguments = vars(self.argument_parser.parse_args())
        self.keyword_arguments = copy.deepcopy(self.arguments)
        for argument in self.exclude_from_kwargs:
            self.keyword_arguments.pop(argument)

    def _initialize_argument_parser(self) -> None:
        # Initialize the argument parser and add the 'verbose' flag
        self.argument_parser = argparse.ArgumentParser(description=__doc__)
        self.argument_parser.add_argument('-v', '--verbose', action='count', default=0,
                                          help='Increase output verbosity, can be used up to '
                                               + '3 times.')
        self.exclude_from_kwargs += ('verbose',)


class CommaSeparatedSummary(nagiosplugin.Summary):
    def ok(self, results) -> str:
        return ', '.join([str(result) for result in results if result.metric])


class ExceptionContext(nagiosplugin.Context):
    def __init__(self, name='exception') -> None:
        super(ExceptionContext, self).__init__(name)

    def evaluate(self, metric: nagiosplugin.Metric,
                 resource: nagiosplugin.Resource) -> nagiosplugin.Result:
        return self.result_cls(nagiosplugin.Critical, str(metric.value), metric)


class DaysValidContext(nagiosplugin.Context):
    fmt_hint = 'less than {value} days'

    def __init__(self, name, check_lifetime=True, warning_days=0, critical_days=0,
                 fmt_metric='Valid for {value} days') -> None:
        super().__init__(name, fmt_metric=fmt_metric)

        self.name = name
        self.check_lifetime = check_lifetime
        self.warning_days = warning_days
        self.critical_days = critical_days
        self.warning = nagiosplugin.Range('@%d:' % self.warning_days)
        self.critical = nagiosplugin.Range('@%d:' % self.critical_days)

    def evaluate(self, metric: nagiosplugin.Metric,
                 resource: nagiosplugin.Resource) -> nagiosplugin.Result:
        if self.check_lifetime and metric.value is not None:
            if self.critical.match(metric.value):
                return nagiosplugin.Result(
                    nagiosplugin.Critical,
                    hint=self.fmt_hint.format(value=self.critical_days),
                    metric=metric
                )
            elif self.warning.match(metric.value):
                return nagiosplugin.Result(
                    nagiosplugin.Warn,
                    hint=self.fmt_hint.format(value=self.warning_days),
                    metric=metric
                )
            else:
                return super(DaysValidContext, self).evaluate(metric, resource)
        else:
            return nagiosplugin.Result(nagiosplugin.Ok)

    def performance(self,
                    metric: nagiosplugin.Metric,
                    resource: nagiosplugin.Resource) -> Optional[nagiosplugin.Performance]:
        if self.check_lifetime and metric.value is not None:
            return nagiosplugin.Performance(self.name, metric.value, '')
        return None


class SelectableSeverityContext(nagiosplugin.Context):
    def __init__(self, name, is_critical):
        super().__init__(name, fmt_metric=self.fmt_metric)
        self._failure_state = nagiosplugin.Critical if is_critical else nagiosplugin.Warn

    @staticmethod
    def fmt_metric(metric, context):
        return None


class ExpectedZeroCountContext(nagiosplugin.Context):
    def __init__(self, name, format_string, suppressed=False):
        self._suppressed = suppressed
        self._format_string = format_string
        super().__init__(name, fmt_metric=self.fmt_metric)

    def fmt_metric(self, metric, context):
        return self._format_string % int(metric.value)

    def evaluate(self, metric, resource):
        if metric.value > 0 and not self._suppressed:
            return self.result_cls(nagiosplugin.Warn, None, metric)
        else:
            return self.result_cls(nagiosplugin.Ok, None, metric)

    def performance(self, metric, resource):
        return nagiosplugin.Performance(label=self.name, value=metric.value, min=0)


class OptionalExactMatchContext(nagiosplugin.Context):
    def __init__(self, name, reference, format_string=None, is_critical=False):
        self._reference = reference
        self._format_string = format_string
        self._failure_state = nagiosplugin.Critical if is_critical else nagiosplugin.Warn
        super().__init__(name, fmt_metric=self.fmt_metric)

    def fmt_metric(self, metric, context):
        if self._format_string:
            value = metric.value if metric.value else 'UNKNOWN'
            return self._format_string % value
        else:
            return metric.value

    def evaluate(self, metric, resource):
        if self._reference:
            if metric.value and metric.value == self._reference:
                return self.result_cls(nagiosplugin.Ok, None, metric)
            else:
                return self.result_cls(self._failure_state, None, metric)
        else:
            return self.result_cls(nagiosplugin.Ok, None, metric)
