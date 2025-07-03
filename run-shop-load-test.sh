#!bin/bash
docker run --rm -v `pwd`:/data -i grafana/k6 run - < shop-load-test.js