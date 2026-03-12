# Stocks Serverless Pipeline (AWS + Terraform + Python + React)

Automated serverless pipeline that:

1. Runs daily on a schedule (EventBridge cron)
2. Computes the biggest mover at 6PM EST from the given watchlist using Massive API Data
3. Stores the daily winner in DynamoDB
4. Exposes `GET/movers` via API Gateway
5. Displays results on a public S3-hosted React SPA

## Watchlist

Configured in lambda.py

- ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"]

## Architecture (High Level)

EventBridge (cron)

- Compute Lambda (lambda.py + movers.py)
- DynamoDB table

API Gateway `GET/movers`

- API Lambda (api_lambda.py)
- Scan DynamoDB table and sort by recent

Frontend (Vite + React)

- fetches API and displays winners

## Prerequisites

- Terraform installed
- AWS credentials configured locally (for `terraform apply`)
- Python available locally
- Massive API key
- AWS CLI (used for `aws s3 sync`)

## Deployment (Backend: Lambdas + API + DynamoDB + Schedule)

### 1. Configure Terraform variables

Create `infrastructure/terraform.tfvars` locally (do not commit):

- `accountId = "YOUR_AWS_ACCOUNT_ID"`
- `massive_api_key = "YOUR_MASSIVE_API_KEY"`

### 2. Build the Lambda deployment (PowerShell)

From repo root:

```powershell
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path build | Out-Null

py -3.13 -m pip install -t .\build requests python-dotenv

Copy-Item .\lambda.py .\build\
Copy-Item .\movers.py .\build\
Copy-Item .\api_lambda.py .\build\

Compress-Archive -Path .\build\* -DestinationPath .\infrastructure\deployment_package.zip -Force
```

### 3. Apply Terraform

```powershell
cd infrastructure
terraform init
terraform apply
```

## Deployment (Frontend (S3 Static Website Hosting))

### 1. Configure API URL for the React build

Create an environment file inside frontend/react

- VITE_API_URL=https://YOUR_REST_API_ID.execute-api.us-east-1.amazonaws.com/prod/movers

### 2. Build and upload

```powershell
cd frontend/react
npm install
npm run build
```

Then upload dist/ to the S3 bucket

```powershell
aws s3 sync dist s3://pennymac-stockserverless-frontend-3214562 --delete
```

## Tradeoffs and Challenges

- Rate limits: Massive free tier is rate-limited, which leads to frequent retry behavior and the need to sleep between calls
- Both of the lambdas share an IAM role for simplicity

## References

- https://www.youtube.com/watch?v=UllPQzVXYtU&t=1s

- https://www.youtube.com/watch?v=DbGo7o9d2So

- https://www.youtube.com/watch?v=00QsYCiWTBA

- https://www.youtube.com/watch?v=pEWOFdcMc6Q

## Deliverables

- Frontend URL: http://pennymac-stockserverless-frontend-3214562.s3-website-us-east-1.amazonaws.com/
- API Endpoint URL: https://bbqfzeac82.execute-api.us-east-1.amazonaws.com/prod/movers
- Github Repo https://github.com/logancol/Stocks-Serverless-Pipeline
