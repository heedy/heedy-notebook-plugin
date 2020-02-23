
.PHONY: clean phony

all: 

#Empty rule for forcing rebuilds
phony:

frontend/node_modules:
	cd frontend; npm i

frontend: phony frontend/node_modules
	cd frontend; npm run build

	
debug: phony frontend/node_modules
	cd frontend; npm run mkdebug

clean:
	# Clear all generated assets for webapp
	rm -rf ./assets/public