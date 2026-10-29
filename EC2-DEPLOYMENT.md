# EC2 demo deployment

The project runs on a single-node K3s cluster in Sydney (`ap-southeast-2`).
Instance: `i-08974f66f0e2f81ce`, `t3.small`, 2 GiB RAM, 20 GiB gp3 root disk.
All eight application services use the demo Helm profile, persistent volumes, and NetworkPolicies.

| Service | URL |
| --- | --- |
| Dashboard | http://dashboard.16.178.123.74.nip.io |
| Store catalog | http://store.16.178.123.74.nip.io/shop/ |
| WordPress admin | http://store.16.178.123.74.nip.io/wp-admin/ |
| MCP endpoint | http://gateway.16.178.123.74.nip.io/mcp |
| Gateway health | http://gateway.16.178.123.74.nip.io/health |

Generated login credentials and demo MCP keys are in the local, git-ignored
`ec2-demo-access.env` file (permissions `0600`). The dashboard uses
`admin@ecommerce.local` and `member@ecommerce.local`; WordPress uses `admin`.
These cloud passwords differ from the repository's local defaults.
The demo endpoints currently use HTTP; TLS is not configured.

Connect and inspect:

```bash
ssh -i ~/Downloads/kubekey.pem ubuntu@16.178.123.74
export KUBECONFIG="$HOME/.kube/config"
kubectl get pods
kubectl top nodes
kubectl top pods
```

On EC2 the chart and scripts are in `/home/ubuntu/kube-ecommerce`.
To reapply the deployed configuration **on EC2**:

```bash
cd ~/kube-ecommerce
export KUBECONFIG="$HOME/.kube/config"
helm upgrade --install ecommerce-stack ./helm/ecommerce-stack \
  -f helm/ecommerce-stack/values-aws.yaml \
  -f helm/ecommerce-stack/values-demo.yaml \
  -f cloud-secrets.json \
  --wait --timeout 10m
```

`cloud-secrets.json` and `demo-access.json` are private files on EC2. Keep them out
of source control and reuse them on upgrades to preserve database passwords and
the WooCommerce API connection. Pod environment variables sourced from changed
Secrets require a rollout restart to take effect.

Application images were built locally for `linux/amd64` and imported into K3s
containerd. Cloud values select `ec2-demo` images, with gateway `ec2-demo-v2`.
Use new tags when rebuilding and import images before upgrading the release.
The demo selects `gemini-3.1-flash-lite` and uses the existing Gemini API key;
chat remains subject to the external provider's availability and quota.

The instance has an automatically assigned public IP. Stopping and starting it
can change that IP; update the ingress domains, WordPress URLs, and access links
if that happens. Rebooting does not normally change it. Data is on the instance's
root EBS disk; this deployment does not configure backups or high availability.
