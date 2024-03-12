current_namespace=demo
delete_types=('service' 'deployment' 'pvc' 'pv' 'configmap')
for delete_type in ${delete_types[@]}
  do
    kubectl get $delete_type --namespace=$current_namespace | awk '{print $1}' | xargs kubectl delete $delete_type --namespace=$current_namespace
  done
