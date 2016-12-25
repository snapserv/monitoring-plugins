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

import nagiosplugin


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
