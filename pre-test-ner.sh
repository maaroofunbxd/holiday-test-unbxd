helm get values ner -nsearch -o yaml > ner-values.yaml
helm install ner-demo ./ner -nsearch \
  -f ner-values.yaml \
  --set replicaCount=1
