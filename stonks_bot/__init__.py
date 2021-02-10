import os

# Init config
from stonks_bot.config import config

environment = os.getenv('STONK_BOT_ENV')
environment = environment if environment else 'default'
conf = config[environment]()

# Init general currency converter as kind of singleton here.
from stonks_bot.currency import Currency

c = Currency()
