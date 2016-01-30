from statistics import mean
from collections import namedtuple

import flask
from flask_wtf import Form
from wtforms.fields import TextAreaField, SubmitField, FloatField
from wtforms import validators, ValidationError

from . import flucalc
from . import keys

version = '0.1.0'

app = flask.Flask(__name__)
app.secret_key = keys.secret_key


FieldError = namedtuple('FieldError', ['field_name', 'message'])

MediaDescription = namedtuple('MediaDescription', ['c', 'd', 'v'])


Values = namedtuple('Values', ['m', 'mu', 'mu_interval'])
CalcResult = namedtuple('CalcResult', ['raw', 'corrected', 'mean_frequency'])


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


dilution_validator = validators.NumberRange(min=1, message='Must be &#8805; 1')


# noinspection PyAttributeOutsideInit
class MultiFloatAreaField(TextAreaField):
    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        if self.data:
            return '\n'.join(self.data)
        return ''

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        data = []
        for pos, value in enumerate(valuelist[0].split(), 1):
            try:
                float_value = float(value)
            except ValueError as e:
                self.data = None
                if len(value) > 5:
                    value = value[:5] + '...'
                message = 'Value #{} is not a valid float: "{}"'.format(pos, value)
                raise ValueError(message) from e
            data.append(float_value)
        self.data = data


class FluctuationInputForm(Form):
    v_total = FloatField('Volume of a culture <i>(&#956;l)</i>, V<sub>tot</sub>',
                         [volume_value], default=200)
    c_selective = MultiFloatAreaField('Observed numbers of clones, C<sub>sel</sub>',
                                      [clones_numbers, int_values])
    d_selective = FloatField('Dilution factor, D<sub>sel</sub>', [dilution_validator])
    v_selective = FloatField('Volume plated <i>(&#956;l)</i>, V<sub>sel</sub>', [volume_value])

    c_complete = MultiFloatAreaField('Observed numbers of clones, C<sub>com</sub>',
                                     [clones_numbers])
    d_complete = FloatField('Dilution factor, D<sub>com</sub>', [dilution_validator])
    v_complete = FloatField('Volume plated <i>(&#956;l)</i>, V<sub>com</sub>', [volume_value])

    submit = SubmitField("Calculate")


@app.route('/', methods=['GET', 'POST'])
def main_page():
    form = FluctuationInputForm(flask.request.form, csrf_enabled=False)
    if not form.is_submitted():
        return flask.render_template('form_with_results.html', form=form, version=version)

    if form.validate():
        result_data = process_input(form)
        return flask.render_template('form_with_results.html', form=form, results=result_data,
                                     version=version)

    for error in get_errors(form):
        message = '<code>{error.field_name}:</code> {error.message}'.format(error=error)
        flask.flash(flask.Markup(message))

    return flask.render_template('form_with_results.html', form=form, version=version)


def get_errors(form):
    for field in form:
        try:
            # extract field symbol
            field_name = field.label.text.rsplit(',', 1)[1].strip()
        except IndexError:
            field_name = field.label.text
        if field.errors:
            message = '; '.join(error.lower().rstrip('.') for error in field.errors)
            yield FieldError(field_name, message)


def process_input(form):
    v_total = form.v_total.data
    selective = MediaDescription(
        c=form.c_selective.data,
        d=form.d_selective.data,
        v=form.v_selective.data
    )
    complete = MediaDescription(
        c=mean(form.c_complete.data),
        d=form.d_complete.data,
        v=form.v_complete.data
    )

    c_complete_to_selective = complete.c * selective.v * complete.d / complete.v / selective.d

    raw_results = calc_raw_results(selective, c_complete_to_selective)
    corrected_results = calc_corrected_results(raw_results, selective, v_total)

    return CalcResult(
        raw=raw_results,
        corrected=corrected_results,
        mean_frequency=mean(flucalc.frequency(r, c_complete_to_selective) for r in selective.c)
    )


def calc_raw_results(selective, c_complete_to_selective):
    m = flucalc.m_mle_estimation(selective.c)
    mu = flucalc.calc_mutation_rate(m, c_complete_to_selective)
    interval = flucalc.mutation_rate_limits(m, mu, len(selective.c))
    return Values(m, mu, interval)


def calc_corrected_results(raw_results, selective, v_total):
    z_selective = calc_z(selective, v_total)
    plating_multiplier = flucalc.plating_efficiency_multiplier(z_selective)
    m = raw_results.m * plating_multiplier
    mu = raw_results.mu * plating_multiplier * z_selective
    interval = flucalc.mutation_rate_limits(m, mu, len(selective.c))
    return Values(m, mu, interval)


def calc_z(media_description, v_total):
    return media_description.v / media_description.d / v_total
