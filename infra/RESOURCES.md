# Provisioned resources

Account `851725336997`, region `ap-south-1`. Everything is tagged
`Project=devops-demo-diva`.

| Resource | Identifier |
| --- | --- |
| EC2 instance | `i-0639b2b0b1f6de573` (t3.small, Amazon Linux 2023, 20 GB gp3, encrypted) |
| Elastic IP | `13.235.101.184` (allocation `eipalloc-046646edfd89869db`) |
| Security group | `sg-0544967d76ac53658` — inbound TCP 80 from 0.0.0.0/0 only |
| DynamoDB table | `diva-shoutouts` — on-demand billing |
| S3 bucket | `diva-shoutout-images-851725336997` — private, AES256, all public access blocked |
| IAM role | `diva-ec2-role` + instance profile `diva-ec2-profile` |
| VPC / subnet | `vpc-0b84a792873b5131d` / `subnet-0bb880102a2c26c0e` (default VPC, ap-south-1a) |

The site is at <http://13.235.101.184/>.

## Access

There is no SSH key and port 22 is closed. Use SSM:

```bash
aws ssm start-session --profile isvadi --region ap-south-1 --target i-0639b2b0b1f6de573
```

## Role permissions

`diva-ec2-role` carries the AWS-managed `AmazonSSMManagedInstanceCore` plus one
inline policy, `diva-app-access`, scoped to exactly what the app needs:

- `dynamodb:PutItem`, `Query`, `GetItem` on the `diva-shoutouts` table only
- `s3:PutObject`, `GetObject` on `diva-shoutout-images-851725336997/images/*` only

No wildcard resources, and no delete permission — the app never removes data.


## Pipeline

| Resource | Identifier |
| --- | --- |
| Pipeline | `diva-shoutout-pipeline` (V2, queued execution mode) |
| Source connection | `diva-github` — `arn:aws:codeconnections:ap-south-1:851725336997:connection/f1ac1085-f248-4b7b-8cb9-d6ad1fa886fb` |
| Build project | `diva-shoutout-build` — `aws/codebuild/standard:7.0`, BUILD_GENERAL1_SMALL |
| Deploy application | `diva-shoutout` / deployment group `diva-shoutout-dg` |
| Artifact bucket | `diva-pipeline-artifacts-851725336997` — versioned, 30-day expiry |
| Roles | `diva-codebuild-role`, `diva-codedeploy-role`, `diva-codepipeline-role` |

The deployment group targets instances by the tag `Name=diva-shoutout-board`, so
replacing the instance needs no pipeline change — just the same tag.

Automatic rollback on failure is enabled. `deploy/hooks/validate.sh` polls the
health endpoint, so a revision that builds but cannot serve is rolled back
rather than left live.

### Data protection

Point-in-time recovery is enabled on `diva-shoutouts`, and the images bucket is
versioned. Both were turned on after a cleanup command deleted live posts that
could not be recovered. Prefer deleting specific keys over a scan-and-delete of
the whole table.

## Teardown additions

## Teardown

```bash
P="--profile isvadi --region ap-south-1"
aws ec2 terminate-instances $P --instance-ids i-0639b2b0b1f6de573
aws ec2 wait instance-terminated $P --instance-ids i-0639b2b0b1f6de573
aws ec2 release-address $P --allocation-id eipalloc-046646edfd89869db
aws ec2 delete-security-group $P --group-id sg-0544967d76ac53658
aws dynamodb delete-table $P --table-name diva-shoutouts
aws s3 rm s3://diva-shoutout-images-851725336997 --recursive --profile isvadi
aws s3api delete-bucket $P --bucket diva-shoutout-images-851725336997
aws iam remove-role-from-instance-profile --profile isvadi \
  --instance-profile-name diva-ec2-profile --role-name diva-ec2-role
aws iam delete-instance-profile --profile isvadi --instance-profile-name diva-ec2-profile
aws iam delete-role-policy --profile isvadi --role-name diva-ec2-role --policy-name diva-app-access
aws iam detach-role-policy --profile isvadi --role-name diva-ec2-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam delete-role --profile isvadi --role-name diva-ec2-role
```

Pipeline resources:

```bash
P="--profile isvadi --region ap-south-1"
aws codepipeline delete-pipeline $P --name diva-shoutout-pipeline
aws codebuild delete-project $P --name diva-shoutout-build
aws deploy delete-deployment-group $P --application-name diva-shoutout --deployment-group-name diva-shoutout-dg
aws deploy delete-application $P --application-name diva-shoutout
aws codeconnections delete-connection $P --connection-arn arn:aws:codeconnections:ap-south-1:851725336997:connection/f1ac1085-f248-4b7b-8cb9-d6ad1fa886fb
aws s3 rm s3://diva-pipeline-artifacts-851725336997 --recursive --profile isvadi
aws s3api delete-bucket $P --bucket diva-pipeline-artifacts-851725336997
for r in codebuild codedeploy codepipeline; do
  aws iam delete-role-policy --profile isvadi --role-name diva-$r-role --policy-name diva-$r-access 2>/dev/null
  aws iam delete-role --profile isvadi --role-name diva-$r-role
done
```
