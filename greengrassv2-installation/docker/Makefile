config:
	python3 config_docker.py
	docker-compose -f docker-compose.yml build

build:
	docker-compose -f docker-compose.yml build
	
start:
	docker-compose up -d
	
stop:
	docker-compose down
	
logs:
	sudo tail -F volumes/gg_root/logs/greengrass.log
	

clean: stop
	pip3 install boto3
	python3 config_docker.py --clean
	chown -R $$USER volumes