all:
pack:
	@python ./tools/pack.py y

upload:
	@python ./tools/make.py upload