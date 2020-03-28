import multiprocessing as mp
import itertools
import logging
from functools import partial
from statistics import mean

import flask

from flucalc import app
from flucalc import flucalc
from flucalc.forms import FluctuationInputForm
from flucalc.types import CalcResult
from flucalc.types import CalcStep
from flucalc.types import FieldError
from flucalc.types import MediaDescription
from flucalc.types import ProcessingResult
from flucalc.types import Values
from flucalc.utils import calc_min_power
from flucalc.utils import format_number_with_power
from flucalc.utils import run_parallel


code_address = 'https://github.com/bondarevts/flucalc'
new_issue_address = code_address + '/issues/new'


@app.route('/', methods=['GET', 'POST'])
def main_page():
    logging.info('Request from ip %s.', flask.request.remote_addr)
    form = FluctuationInputForm(flask.request.form)
    render_page_template = partial(
        flask.render_template,
        'form_with_results.html',
        format_number_with_power=format_number_with_power, form=form, version=app.config['VERSION']
    )
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
            result = run_parallel(
                solve,
                args=(v_total, selective, complete),
                timeout=app.config['CALCULATION_TIMEOUT_SEC']
            )
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


def calc_frequencies(selective, complete):
    return [flucalc.frequency(c_sel, c_com * selective.v * complete.d / complete.v / selective.d)
            for c_sel, c_com in zip(selective.c, itertools.cycle(complete.c))]


def solve(v_total, selective, complete):
    def calc_raw_results():
        m = flucalc.m_mle_estimation(selective.c)
        add_step(1, 'Number of mutations, m', m, 'm_raw')

        mu = flucalc.calc_mutation_rate(m, n_total)
        add_step(4, 'Mutation rate, &mu;', mu, 'mu_raw')

        interval = flucalc.mutation_rate_limits(m, len(selective.c), n_total)
        add_step(5, 'Lower limit for mutation rate, &mu;<sup>&minus;</sup>', interval.lower, 'mu_raw_lower')
        add_step(6, 'Upper limit for mutation rate, &mu;<sup>+</sup>', interval.upper, 'mu_raw_upper')

        return Values(m, mu, interval, calc_min_power(mu, *interval))

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
        return Values(m, mu, interval, calc_min_power(mu, *interval))

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
