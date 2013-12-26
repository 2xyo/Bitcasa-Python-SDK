# Bitcasa List Directory Example *
# 2013 Michael Thomas (Biscuit Labs) #

from Bitcasa import Bitcasa

client = Bitcasa.Client('config.json')
print("### Bitcasa List Directory Example ###")
root_dir = client.dir();
drive_path = ""
print("### Printing Bitcasa Root Directory ###")
for files in root_dir:
	print(files['name'] + " - " + files['path'])
	if(files['name'] == "Bitcasa Infinite Drive"):
		drive_path = files['path']