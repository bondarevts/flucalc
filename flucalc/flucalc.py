import math
from functools import lru_cache
from collections import Counter
from statistics import median, mean

from scipy import optimize


# All notations were taken from article [Foster et al., 2006]


@lru_cache(maxsize=None)
def cultures_ratio(mutations_per_culture, mutants_count):
    """ Calculate proportion of cultures with `mutants_count` mutants.

    Recursive algorithm were taken from [Sarkar et al., 1992].

    :param mutations_per_culture: number of mutations per culture; denoted by m
    :param mutants_count: observed number of mutants in a culture; denoted by r
    :return: p_r for given m. 0 <= p_r <= 1
    :rtype: float
    """
    if mutants_count == 0:
        return math.exp(-mutations_per_culture)

    return (mutations_per_culture / mutants_count *
            sum(cultures_ratio(mutations_per_culture, i) / (mutants_count + 1 - i)
                for i in range(mutants_count)))


def get_start_guess_for_number_of_mutations(observed_mutant_counts):
    def m_estimation_func(m):
        return abs(r_med / m - math.log(m) - 1.24)

    r_med = median(observed_mutant_counts)

    # 0.3 is our default guess for mutants count per culture
    return _optimize_positive_value(m_estimation_func, guess=0.3)


def estimate_number_of_mutations_by_mle(observed_mutant_counts):
    def min_log_likelihood(m, counts=Counter(observed_mutant_counts)):
        s = -sum(counts[r] * math.log(cultures_ratio(m, r)) for r in range(max(counts) + 1))
        return s

    start_guess = get_start_guess_for_number_of_mutations(observed_mutant_counts)
    return _optimize_positive_value(min_log_likelihood, guess=start_guess)


def mutation_rate_limits(mutations_count, mu, cultures_count):
    def ci_lower_estimation(value):
        return abs(value - math.log(mutations_count) -
                   2.401 * math.exp(-0.315 * value) / math.sqrt(cultures_count))

    def ci_upper_estimation(value):
        return abs(value - math.log(mutations_count) +
                   2.401 * math.exp(-0.315 * value) / math.sqrt(cultures_count))

    lower = _optimize_positive_value(ci_lower_estimation, guess=1)
    upper = _optimize_positive_value(ci_upper_estimation, guess=1)

    mu_lower = math.exp(lower - math.log(mutations_count)) * mu
    mu_upper = math.exp(upper - math.log(mutations_count)) * mu
    return mu_lower, mu_upper


def calc_mutation_rate(observed_mutant_counts, cells_in_culture):
    mutations_count = estimate_number_of_mutations_by_mle(observed_mutant_counts)

    mu = mutations_count / mean(cells_in_culture)
    limits = mutation_rate_limits(mutations_count, mu, len(observed_mutant_counts))

    return mu, limits


def calc_frequency(observed_mutant_counts, numbers_of_cells_in_cultures):
    return [mutant_count / cells_count
            for mutant_count, cells_count in zip(observed_mutant_counts,
                                                 numbers_of_cells_in_cultures)]


def _optimize_positive_value(func, *, guess):
    """ argmin(func), where func: R+ -> R """
    return optimize.minimize(lambda x: func(x[0]), [guess], bounds=[(1e-10, None)])['x'][0]


def main():
    observed_mutant_counts = [22, 16, 44, 39, 26, 36, 35, 19, 26, 25, 35, 33]
    print(estimate_number_of_mutations_by_mle(observed_mutant_counts))
    print(calc_mutation_rate(observed_mutant_counts, [1.2e8]))


if __name__ == '__main__':
    main()
