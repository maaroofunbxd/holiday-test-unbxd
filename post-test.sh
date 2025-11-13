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