all:
pack:
	@python ./tools/pack.py pack

setup:
	@python ./tools/make.py setup

upload:
	@python ./tools/make.py upload