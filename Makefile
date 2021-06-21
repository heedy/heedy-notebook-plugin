VERSION:=$(shell cat VERSION)-git.$(shell git rev-list --count HEAD)

.PHONY: clean phony

all: build

#Empty rule for forcing rebuilds
phony:

build: frontend
	# Remove original mjs files in production builds
	find ./dist/notebook/public/static -name "*.gz" -exec sh -c 'rm "$${0%.gz}"' {} ';'
	cd dist;zip -r heedy-notebook-plugin-${VERSION}.zip ./notebook

dist/notebook: node_modules
	mkdir -p dist/notebook
	cp LICENSE ./dist/notebook
	cp VERSION ./dist/notebook
	cp requirements.txt ./dist/notebook
	cp -r ipynb ./dist/notebook
	npm run build

node_modules:
	npm i

frontend/node_modules:
	cd frontend; npm i

frontend: phony dist/notebook frontend/node_modules
	cd frontend; npm run build

	
debug: phony frontend/node_modules dist/notebook
	npm run debug

clean:
	rm -rf ./dist
	rm -rf ./node_modules
	rm -rf ./frontend/node_modules