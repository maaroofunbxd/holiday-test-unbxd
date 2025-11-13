kubectl get events -nsearch --field-selector involvedObject.kind=Pod --sort-by=.lastTimestamp -A \
  -o custom-columns=NAMESPACE:.metadata.namespace,TIME:.lastTimestamp,TYPE:.type,REASON:.reason,MESSAGE:.message \
  | grep -E "ranking|Successful(Create|Delete)" \
  | awk -v now="$(date -u +%s)" '
  NR==1 {print; next}  # print header
  {
    match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z/, t)
    if (t[0] != "") {
      cmd = "date -u -d \"" t[0] "\" +%s"
      cmd | getline ts
      close(cmd)
      if (now - ts <= 1200) print $0   # 1200 sec = 20 min
    }
  }'

kubectl get pods -nsearch -l'algo in (ranking,embeddings)' -w
# NAME                                                              READY   STATUS    RESTARTS      AGE
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76ccxprs   2/2     Running   0             54d
# embeddings-9c649214ad-predictor-00001-deployment-9cffc6898vz8jb   2/2     Running   0             307d
# ranking-2fdac0ba40-predictor-00722-deployment-6dcff45f5b-4v964    2/2     Running   2 (20d ago)   21d
# ranking-51413b6089-predictor-00753-deployment-65d5489f8d-8ztk5    2/2     Running   0             21d
# ranking-b26742c69c-predictor-00651-deployment-565b85584-jnk2m     2/2     Running   0             21d
# ranking-b7ce3d0cbe-predictor-00743-deployment-5dbd7c47cc-x7vqp    2/2     Running   0             2d12h
# ranking-ce9a583517-predictor-00492-deployment-cdd6bcdf5-54z6j     2/2     Running   0             15h
# ranking-e03d816cfc-predictor-00186-deployment-57cfbf6778-lq58z    2/2     Running   0             21d
# ranking-ec7d9fa992-predictor-00328-deployment-f646874b5-l8hg6     2/2     Running   0             27h
# ranking-f5d092cddd-predictor-00712-deployment-6c78d8566f-g4zd2    2/2     Running   0             11h
# ranking-f68e76d65c-predictor-00529-deployment-584ffdb879-478x2    2/2     Running   0             23h
# ranking-f68e76d65c-predictor-00529-deployment-584ffdb879-l7dzq    2/2     Running   0             44s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             0s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             0s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             54s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             66s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             77s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             87s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             97s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             107s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             117s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             2m8s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             2m25s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             2m47s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             2m58s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             3m8s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     Pending   0             3m18s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   0/2     ContainerCreating   0             3m18s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   1/2     Running             0             5m22s
# embeddings-948f73f720-predictor-00007-deployment-b6c4cf76cwsl2s   2/2     Running             0             5m58s