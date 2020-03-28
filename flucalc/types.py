from collections import namedtuple

MediaDescription = namedtuple('MediaDescription', ['c', 'd', 'v'])

FieldError = namedtuple('FieldError', ['field_name', 'message'])


Values = namedtuple('Values', ['m', 'mu', 'mu_interval', 'power'])
CalcResult = namedtuple('CalcResult', ['raw', 'corrected', 'mean_frequency'])

CalcStep = namedtuple('CalcStep', ['pos', 'description', 'value', 'img'])

ProcessingResult = namedtuple('ProcessingResult', ['values', 'steps'])
