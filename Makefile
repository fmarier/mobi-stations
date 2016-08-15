all:

clean:
	find -name "*.pyc" -delete

pyflakes:
	@echo Running pyflakes...
	@pyflakes3 *.py

pep257:
	@echo Running pep257...
	@pep257 *.py

pep8:
	@echo Running pep8...
	@pep8 --ignore=E501 *.py

codespell:
	@echo Running codespell...
	@codespell *.py

lint:
	@echo Running pylint...
	@pylint3 --rcfile=.pylintrc *.py

test: pep8 pyflakes lint codespell
