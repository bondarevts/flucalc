from wtforms import ValidationError
from wtforms import validators


def volume_value(_, field):
    if field.data is not None and float(field.data) <= 0:
        raise ValidationError('Non positive volume')


def clones_numbers(_, field):
    if field.data is not None:
        if any(clone < 0 for clone in field.data):
            raise ValidationError('Negative number of clones')


def int_values(_, field):
    if field.data is not None:
        if not all(value.is_integer() for value in field.data):
            raise ValidationError('Number must be integer')


dilution_validator = validators.NumberRange(min=1, message='Must be &ge; 1')
