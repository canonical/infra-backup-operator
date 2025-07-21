# Infra Backup Operator

The Infra Backup Operator is a Juju charm that configures automated backups of non-workload-related
Kubernetes resources in **any** Kubernetes cluster. It integrates with the velero-operator charm to
schedule and manage backups of critical infrastructure components, ensuring resilience and
disaster recovery readiness.

🔧 What It Does
This charm defines the backup of:

* All cluster-scoped resources (e.g., CRDs, CSRs, ClusterRoles, StorageClasses, etc.) will be
backed up, **except for PersistentVolumes (PVs)**, which are considered workload-related rather
than part of the core infrastructure.

* Namespaced resources in:
    * kube-system — includes configurations for critical components such as CoreDNS, Cilium, and k8s-gateway.

    * kube-public — typically contains publicly accessible, cluster-wide information

    * metallb-system — if this namespace exists, its resources are backed up as well.

        🔹 This namespace will be present in Canonical Kubernetes deployments when LoadBalancer
        is enabled, as it hosts the MetalLB controller and configuration.

* The following resources on **all** namespaces:
    * Role, RoleBinding
    * NetworkPolicy
    * ResourceQuota
    * LimitRange
    * ServiceAccount
    * Gateway and Routes (HttpRoute, TCPRoute)
    * Ingress
    * Namespaces
    * ConfigMap
    * Secret
    * HPA / VPA
    * Jobs
    * CronJobs

By focusing only on infrastructure data, this charm complements application-level backup strategies
without overlapping responsibilities. It ensures that cluster state and operational configuration
can be restored independently from user workloads.

🎯 Key Features
Integrates with the velero-operator charm via Juju relations

Automatically defines backup targets for platform-level resources

Excludes ephemeral or workload-specific namespaces by design

Provides a clean separation between infra backup and app-level backup

💡 When to Use This Charm
Use this charm when you want to:

Implement a cluster-level backup strategy without interfering with app workloads

Ensure your Kubernetes infrastructure can be restored in a clean and consistent way

Provide platform SREs with control over infra backups, while allowing application teams
to manage their own.


## Other resources

* [Contributing](CONTRIBUTING.md) <!-- or link to other contribution documentation -->

* See the [Juju SDK documentation](https://juju.is/docs/sdk) for more information about developing and improving charms.
