# Bitcasa Upload Example *
# 2013 Michael Thomas (Biscuit Labs) #

from Bitcasa import Bitcasa

client = Bitcasa.Client('config.json')
print("Test Upload Engaged")
client.write("/","test.block")