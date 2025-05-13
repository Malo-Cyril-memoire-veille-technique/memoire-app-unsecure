# memoire-app-unsecure
messagerie pas sécurisée

docker compose up
docker-compose run --rm -it poc-server
docker-compose run mitm-proxy
docker-compose run client_a
docker-compose run client_b