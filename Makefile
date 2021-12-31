VERSION:=$(shell cat VERSION)
PLUGIN_NAME:=notebook

HEEDY:=$(shell test -f ./heedy && echo "./")heedy

.PHONY: clean clear watch debug release run


release: node_modules clear dist/notebook
	npm run build
	# Remove original files of pre-compressed content
	if test -d ./dist/notebook/public/static; then find ./dist/notebook/public/static -name "*.gz" -exec sh -c 'rm "$${0%.gz}"' {} ';';fi
	# Zip the plugin
	cd dist;zip -r heedy-notebook-plugin-${VERSION}.zip ./notebook

node_modules:
	if test -d frontend; then (cd frontend && npm i);fi
	npm i

dist/notebook:
	mkdir -p dist/notebook

testdb:
	$(HEEDY) create testdb --noserver --username=test --password=test
	mkdir testdb/plugins
	cd testdb/plugins; ln -s ../../dist/notebook notebook

debug: node_modules dist/notebook testdb
	npm run debug

watch: node_modules dist/notebook testdb
	npm run watch

run: testdb
	$(HEEDY) run testdb --verbose

clear:
	rm -rf dist

clean: clear
	rm -rf testdb
	if test -d node_modules; then rm -rf node_modules; fi
	if test -d frontend/node_modules; then rm -rf frontend/node_modules; fi

rename: clean
	find ./ -type f -exec sed -i -e 's/notebook/$(PLUGIN_NAME)/g' {} \;
