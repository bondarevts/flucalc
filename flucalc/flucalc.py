import math
from functools import lru_cache
from collections import Counter
from statistics import median, mean

from scipy import optimize


# All notations were taken from article [Foster, 2006]

# Full list of references:
#
# Foster, P.L. (2006). Methods for Determining Spontaneous Mutation Rates.
#
# Sarkar, S., Ma, W. T., and Sandri, G.v.H. (1992). On fluctuation analysis: A new, simple
#     and efficient method for computing the expected number of mutants.
#
# Lea, D. E., and Coulson, C. A. (1949). The distribution of the numbers of mutants
#     in bacterial populations.
#
# Stewart, F. M. (1994). Fluctuation tests: How reliable are the estimates of mutation rates?

@lru_cache(maxsize=None)
def cultures_ratio(m, r):
    """ Calculate proportion of cultures with `r` mutants.
    Denoted by p_r.

    Recursive algorithm were taken from [Sarkar et al., 1992].

    :param m: number of mutations per culture
    :param r: observed number of mutants in a culture
    :return: p_r for given m; 0 <= p_r <= 1
    """
    if r == 0:
        return math.exp(-m)

    return m / r * sum(cultures_ratio(m, i) / (r + 1 - i) for i in range(r))


def get_start_m_approximation(r_observed):
    """ Get good start guess point for number of mutations per culture.

    Calculate start approximation of m by equation from [Lea, Coulson, 1945].

    :param r_observed: list of observed number of mutants
    :return: approximation of number of mutations per culture
    """
    def calc_estimation(m):
        return abs(r_median / m - math.log(m) - 1.24)

    r_median = median(r_observed)

    # 0.3 is our default guess for mutants count per culture
    return _optimize_positive_value(calc_estimation, guess=0.3)


def m_mle_estimation(r_observed):
    """ Calculate estimated value for number of mutants per culture by MSS-MLE.
    todo расшифровка
    Likelihood function were taken from [Foster, 2006] with log transformation.

    :param r_observed: list of observed number of mutants
    :return: estimated value for number of mutants per culture
    """
    def min_log_likelihood(m, counts=Counter(r_observed)):
        return -sum(counts[r] * math.log(cultures_ratio(m, r)) for r in range(max(counts) + 1))

    start_guess = get_start_m_approximation(r_observed)
    return _optimize_positive_value(min_log_likelihood, guess=start_guess)


def mutation_rate_limits(m, mu, c):
    """ 95% confidence interval bounds estimation for mutation rate.

    Estimation of bounds calculated from equation from [Stewart, 1994]

    :param c: count of cultures; denoted by C
    :param mu: mutation rate: probability of mutation per cell per division or generation
    :param m: number of mutations per culture
    """
    def ci_lower_estimation(value):
        return abs(value - math.log(m) + 2.401 * math.exp(-0.315 * value) / math.sqrt(c))

    def ci_upper_estimation(value):
        return abs(value - math.log(m) - 2.401 * math.exp(-0.315 * value) / math.sqrt(c))

    lower = _optimize_positive_value(ci_lower_estimation, guess=1)
    upper = _optimize_positive_value(ci_upper_estimation, guess=1)

    mu_lower = math.exp(lower - math.log(m)) * mu
    mu_upper = math.exp(upper - math.log(m)) * mu
    return mu_lower, mu_upper


def calc_mutation_rate(r_observed, cells_in_culture):
    """ Calculate mutation rate (denoted by mu).

    mu = m / (mean number of cells in culture)
    where m is a number of mutants per culture.

    :param r_observed: list of observed number of mutants
    :param cells_in_culture: list of cell numbers in cultures
    :return: mu with bounds tuple: (mu, (lower_mu_bound, upper_mu_bound))
    """
    m = m_mle_estimation(r_observed)

    n_total = mean(cells_in_culture)
    mu = m / n_total
    limits = mutation_rate_limits(m, mu, len(r_observed))

    return mu, limits


def calc_frequency(observed_mutant_count, number_of_cells):
    """ Calculate mutation fraction (or frequency) per culture.

    Frequency calculated as r/N.
    where r is observed number of mutants
          N is a number of cells in a culture

    :param observed_mutant_count: observed number of mutants in a culture
    :param number_of_cells: number of cells in a culture
    :return: mutation fraction per culture
    """
    return observed_mutant_count / number_of_cells


def _optimize_positive_value(func, *, guess):
    """ argmin(func), where func: R+ -> R """
    return optimize.minimize(lambda x: func(x[0]), [guess], bounds=[(1e-10, None)])['x'][0]


def main():
    observed_mutant_counts = [22, 16, 44, 39, 26, 36, 35, 19, 26, 25, 35, 33]
    print('m = ', m_mle_estimation(observed_mutant_counts))
    mu, (lower, upper) = calc_mutation_rate(observed_mutant_counts, [1.2e8])
    print('mu = {}, {} < mu < {} (* 10^8)'.format(mu * 1e8, lower * 1e8, upper * 1e8))


if __name__ == '__main__':
    main()
