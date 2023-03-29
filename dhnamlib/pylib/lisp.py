
from itertools import chain

from dhnamlib.pylib.iteration import partition
from dhnamlib.pylib.iteration import split_by_indices


def parse_hy_args(symbols):
    '''
    e.g. parse_hy_args(*'100 200 300 :x 400 :y 500'.split())
    '''
    args = []

    for idx, symbol in enumerate(symbols):
        if symbol.startswith(':'):
            break
        else:
            args.append(symbol)
    else:
        idx += 1

    def remove_colon(k):
        assert k[0] == ':'
        return k[1:]

    pairs = partition(symbols[idx:], 2)
    kwargs = dict((remove_colon(k), v) for k, v in pairs)

    return args, kwargs


def get_prefixed_paren_index_pairs(text, info_dicts=[dict(prefix="'", paren_pair='()')], recursive=False):
    # https://stackoverflow.com/a/29992019

    '''
    e.g.
    >>> text = "(a b '(c d '(e f)))"
    >>> info_and_index_pair_tuples = get_prefixed_paren_index_pairs(text)
    >>> info_dict, index_pair = info_and_index_pair_tuples[0]
    >>> text[index_pair[0]: index_pair[1] + 1]  # index_pair[0] and index_pair[1] mean the indices of the opening and closing parentheses

    "(c d '(e f))"
    '''
    # return a list of (prefix, index_pair)
    # use info_dicts

    info_tuples = tuple(tuple([info_dict['prefix'], info_dict['paren_pair']]) for info_dict in info_dicts)
    l_to_r_paren = dict(pair for prefix, pair in info_tuples)
    l_parens, r_parens = map(set, zip(*l_to_r_paren.items()))

    opening_stack = []  # stack of indices of opening parentheses
    info_and_index_pair_tuples = []
    num_prefixed_exprs_under_parsing = 0

    def match_prefix(past_char, prefix):
        if len(past_chars) >= len(prefix):
            return all(past_char == prefix_char
                       for past_char, prefix_char in zip(reversed(past_chars), reversed(prefix)))
        else:
            return False

    past_chars = []
    for char_idx, char in enumerate(text):
        if char in l_parens:
            for info_idx, (prefix, (l_paren, r_paren)) in enumerate(info_tuples):
                if char == l_paren and match_prefix(past_chars, prefix):
                    num_prefixed_exprs_under_parsing += 1
                    break
            else:
                info_idx = None
            opening_stack.append((char_idx, info_idx))
        elif char in r_parens:
            try:
                l_paren_idx, info_idx = opening_stack.pop()
                assert l_to_r_paren[text[l_paren_idx]] == char
                if info_idx is not None:
                    num_prefixed_exprs_under_parsing -= 1
                    if recursive or num_prefixed_exprs_under_parsing == 0:
                        info_and_index_pair_tuples.append((info_dicts[info_idx], (l_paren_idx, char_idx)))
            except IndexError:
                print('Too many closing parentheses')
        past_chars.append(char)
    if opening_stack:
        print('Too many opening parentheses')

    return info_and_index_pair_tuples


def remove_comments(text):
    splits = text.split('\n')
    # only remove lines that starts with comments
    return '\n'.join(split for split in splits if not split.lstrip().startswith(';'))


def replace_prefixed_parens(text, info_dicts):
    info_and_index_pair_tuples = get_prefixed_paren_index_pairs(text, info_dicts)
    prev_r_index = 0
    splits = []
    for info_dict, (l_index, r_index) in info_and_index_pair_tuples:
        splits.append(text[prev_r_index + 1: l_index - len(info_dict['prefix'])])
        splits.append(info_dict['fn'](text[l_index: r_index + 1]))
        prev_r_index = r_index
    splits.append(text[prev_r_index + 1:])
    return ''.join(splits)
