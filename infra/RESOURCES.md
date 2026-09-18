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
