from argparse import ArgumentParser
from typing import Union, List, Any

from telegram import Update

from stonks_bot.helper.message import reply_gif_wrong_arg_help, reply_gif_symbol_missing

parser_symbol = ArgumentParser(description='Symbol to lookup-')
parser_symbol.add_argument('symbol', nargs=1, type=str, help='What symbol do you want to lookup?')


def parse_symbol(update: Update, args: List[Any]) -> Union[bool, str]:
    try:
        args = parser_symbol.parse_args(args)
        result = args.symbol
    except:
        reply_gif_symbol_missing(update)

        result = False

    return result


parser_daily_perf_count = ArgumentParser(description='Daily performance count parser.')
parser_daily_perf_count.add_argument('count', nargs='?', default=15, type=int, help='How many rows to show?')


def parse_daily_perf_count(update: Update, args: List[Any]) -> int:
    try:
        args = parser_daily_perf_count.parse_args(args)
        result = args.count
    except:
        reply_gif_wrong_arg_help(update)

        result = parser_daily_perf_count.get_default('count')

    return result
