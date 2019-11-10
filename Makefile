
.PHONY: clean test phony

all: 

#Empty rule for forcing rebuilds
phony:

frontend/node_modules:
	cd frontend; npm i

frontend: phony frontend/node_modules
	cd frontend; npm run build

server: backend/main.go phony # gencode
	cd backend; $(GO) build --tags "sqlite_foreign_keys json1 sqlite_preupdate_hook" -o ../assets/server

standalone: server frontend
	
debug: phony frontend/node_modules
	cd frontend; npm run mkdebug

clean:
	# Clear all generated assets for webapp
	rm -rf ./assets/public