import nagiosplugin


class ExceptionContext(nagiosplugin.Context):
    def __init__(self, name):
        super(ExceptionContext, self).__init__(name)

    def evaluate(self, metric, resource):
        return self.result_cls(nagiosplugin.Critical, str(metric.value), metric)
