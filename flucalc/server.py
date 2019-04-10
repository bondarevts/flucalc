import itertools
import logging
import math
import multiprocessing as mp
from collections import namedtuple
from functools import partial
from statistics import mean

import flask
from flask_wtf import Form
from wtforms import ValidationError
from wtforms import validators
from wtforms.fields import FloatField
from wtforms.fields import SubmitField
from wtforms.fields import TextAreaField

from . import flucalc
from . import keys

CALCULATION_TIMEOUT_SEC = 5

version = '2017.9.1'
code_address = 'https://github.com/bondarevts/flucalc'
new_issue_address = code_address + '/issues/new'

logging_level = logging.INFO
logging.basicConfig(filename='flucalc.log', level=logging_level,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

app = flask.Flask(__name__)
app.secret_key = keys.secret_key


FieldError = namedtuple('FieldError', ['field_name', 'message'])

MediaDescription = namedtuple('MediaDescription', ['c', 'd', 'v'])


Values = namedtuple('Values', ['m', 'mu', 'mu_interval', 'power'])
CalcResult = namedtuple('CalcResult', ['raw', 'corrected', 'mean_frequency'])

CalcStep = namedtuple('CalcStep', ['pos', 'description', 'value', 'img'])

ProcessingResult = namedtuple('ProcessingResult', ['values', 'steps'])


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
    v_total = FloatField('Volume of a culture <i>(&mu;l)</i>, V<sub>tot</sub>',
                         [volume_value], default=200)
    c_selective = MultiFloatAreaField('Observed numbers of clones, C<sub>sel</sub>',
                                      [clones_numbers, int_values])
    d_selective = FloatField('Dilution factor, D<sub>sel</sub>', [dilution_validator])
    v_selective = FloatField('Volume plated <i>(&mu;l)</i>, V<sub>sel</sub>', [volume_value])

    c_complete = MultiFloatAreaField('Observed numbers of clones, C<sub>com</sub>',
                                     [clones_numbers])
    d_complete = FloatField('Dilution factor, D<sub>com</sub>', [dilution_validator])
    v_complete = FloatField('Volume plated <i>(&mu;l)</i>, V<sub>com</sub>', [volume_value])

    submit = SubmitField('Calculate')

    def __repr__(self):
        c_sel = ';'.join(self.c_selective.raw_data[0].split())
        c_com = ';'.join(self.c_complete.raw_data[0].split())
        return 'V_tot={}|C_sel={}|D_sel={}|V_sel={}|C_com={}|D_com={}|V_com={}'.format(
            self.v_total.raw_data[0],
            c_sel, self.d_selective.raw_data[0], self.v_selective.raw_data[0],
            c_com, self.d_complete.raw_data[0], self.v_complete.raw_data[0]
        )


@app.route('/', methods=['GET', 'POST'])
def main_page():
    logging.info('Request from ip %s.', flask.request.remote_addr)
    form = FluctuationInputForm(flask.request.form, csrf_enabled=False)
    render_page_template = partial(flask.render_template,
                                   'form_with_results.html',
                                   format_number_with_power=format_number_with_power,
                                   form=form, version=version)
    if not form.is_submitted():
        return render_page_template()

    logging.info('Form submitted: %s', form)

    if form.validate():
        logging.info('Form validated')
        v_total = form.v_total.data
        selective = MediaDescription(
            c=form.c_selective.data,
            d=form.d_selective.data,
            v=form.v_selective.data
        )
        complete = MediaDescription(
            c=form.c_complete.data,
            d=form.d_complete.data,
            v=form.v_complete.data
        )

        if 'calc-freq' in flask.request.form:
            if len(selective.c) != len(complete.c):
                complete = complete._replace(c=[mean(complete.c)])
                message = 'Frequency was calculated using mean of C<sub>com</sub>'
                flask.flash(flask.Markup(message))
            frequencies = calc_frequencies(selective, complete)
            return render_page_template(frequencies=frequencies)

        complete = complete._replace(c=mean(complete.c))

        try:
            result = run_parallel(solve, args=(v_total, selective, complete), timeout=CALCULATION_TIMEOUT_SEC)
        except mp.TimeoutError:
            message = 'Calculation failed. Possible C<sub>sel</sub> too big.'
            logging.info(message)
            flask.flash(flask.Markup(message))
            return render_page_template()
        except Exception:
            message = ('Calculation failed. '
                       'If it is repeated please <a href="{}">create an issue</a>.'.format(new_issue_address))
            logging.exception(message)
            flask.flash(flask.Markup(message))
            return render_page_template()
        return render_page_template(results=result.values, process=result.steps)

    for error in get_errors(form):
        message = '<code>{error.field_name}:</code> {error.message}'.format(error=error)
        logging.info('Form error. %s: %s', error.field_name, error.message)
        flask.flash(flask.Markup(message))

    return render_page_template()


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


def _calc_min_power(*values):
    return int(min(math.floor(math.log10(value)) for value in values))


def format_number_with_power(number, power, precision=4):
    return '{0:.{1}f}e{2:+03d}'.format(number / pow(10, power), precision, power)


def calc_frequencies(selective, complete):
    return [flucalc.frequency(c_sel, c_com * selective.v * complete.d / complete.v / selective.d)
            for c_sel, c_com in zip(selective.c, itertools.cycle(complete.c))]


def apply_function_to_pipe(func, args, kwargs, pipe):
    try:
        pipe.send(func(*args, **kwargs))
    except Exception:
        logging.exception('Processing error')


def run_parallel(func, args=(), kwargs=None, timeout=None):
    if kwargs is None:
        kwargs = {}

    ctx = mp.get_context('spawn')
    out_pipe, in_pipe = ctx.Pipe(duplex=False)
    process = ctx.Process(target=apply_function_to_pipe, args=(func, args, kwargs, in_pipe))
    process.daemon = True
    process.start()
    logging.info('Process started')
    logging.info('Run calculation in process %s', process.pid)
    process.join(timeout=timeout)
    if not process.is_alive():
        logging.info('Calculation finished')
        return out_pipe.recv()

    logging.info('Try to terminate process')
    process.terminate()
    process.terminate()
    logging.info('Calculation terminated by timeout')
    raise mp.TimeoutError


def solve(v_total, selective, complete):
    def calc_raw_results():
        m = flucalc.m_mle_estimation(selective.c)
        add_step(1, 'Number of mutations, m', m, 'm_raw')

        mu = flucalc.calc_mutation_rate(m, n_total)
        add_step(4, 'Mutation rate, &mu;', mu, 'mu_raw')

        interval = flucalc.mutation_rate_limits(m, len(selective.c), n_total)
        add_step(5, 'Lower limit for mutation rate, &mu;<sup>&minus;</sup>', interval.lower, 'mu_raw_lower')
        add_step(6, 'Upper limit for mutation rate, &mu;<sup>+</sup>', interval.upper, 'mu_raw_upper')

        return Values(m, mu, interval, _calc_min_power(mu, *interval))

    def calc_corrected_results(raw):
        z_selective = calc_z(selective)
        add_step(7, 'Fraction of a culture plated on selective media, z<sub>sel</sub>', z_selective, 'z_sel')

        plating_multiplier = flucalc.plating_efficiency_multiplier(z_selective)
        add_step(8, 'Plating efficiency multiplier, &omega;', plating_multiplier, 'plating_efficiency')

        m = raw.m * plating_multiplier
        add_step(9, 'Corrected number of mutations, m<sub>&omega;</sub>', m, 'm_corr')

        mu = flucalc.calc_mutation_rate(m, n_total)
        add_step(10, 'Corrected mutation rate, &mu;<sub>&omega;</sub>', mu, 'mu_corr')

        interval = flucalc.Interval(
            lower=raw.mu_interval.lower * plating_multiplier,
            upper=raw.mu_interval.upper * plating_multiplier,
        )
        add_step(11, 'Corrected lower limit for mutation rate, '
                     '&mu;<span style="position: relative;"><sub>&omega;</sub>'
                     '<sup style="position: absolute; left: 0;">&minus;</sup><span>',
                 interval.lower, 'mu_corr_lower')
        add_step(12, 'Corrected upper limit for mutation rate, '
                     '&mu;<span style="position: relative;"><sub>&omega;</sub>'
                     '<sup style="position: absolute; left: 0;">+</sup><span>',
                 interval.upper, 'mu_corr_upper')
        return Values(m, mu, interval, _calc_min_power(mu, *interval))

    def calc_z(media_description):
        return media_description.v / media_description.d / v_total

    def add_step(position, description, value, img=None):
        steps.append(CalcStep(position, description, float(value), img))

    steps = []
    logging.info('Start calculation')

    add_step(2, 'Mean of C<sub>com</sub>', complete.c, 'mean_c_com')

    n_total = complete.c * complete.d * v_total / complete.v
    add_step(3, 'Total number of cells in culture, N<sub>tot</sub>', n_total, 'n_total')

    logging.info('Raw results calculation')
    raw_results = calc_raw_results()

    logging.info('Corrected results calculation')
    corrected_results = calc_corrected_results(raw_results)

    logging.info('Frequency calculation')

    c_complete_to_selective = complete.c * selective.v * complete.d / complete.v / selective.d
    add_step(13, 'C<sub>com</sub> adjusted to selective media', c_complete_to_selective, 'c_com_sel')

    frequency = mean(flucalc.frequency(r, c_complete_to_selective) for r in selective.c)
    add_step(14, 'Mean frequency, <span style="border-top:1px solid black">f</span>', frequency, 'frequency')
    steps.sort()

    result = CalcResult(
        raw=raw_results,
        corrected=corrected_results,
        mean_frequency=frequency
    )
    return ProcessingResult(steps=steps, values=result)
