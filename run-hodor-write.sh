#!bin/bash
docker run --rm -v `pwd`:/data -i grafana/k6 run - < hodor-write-test.js