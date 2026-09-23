## CI/CD, Releases and Deployment
### CI/CD Pipelines
<!-- field id=smtd.pipelines required=yes na=no source=cicd hint="Each pipeline: tool, trigger, stages, quality gates, where to find runs and logs, who maintains it" -->
### Release Management
<!-- field id=smtd.release-mgmt required=yes na=no source=releases hint="Release cadence, approval and change-management process, release calendar, freeze periods, communication of releases" -->
### Deployment Strategy
<!-- field id=smtd.deploy-strategy required=yes na=no source=releases hint="Blue/green, canary, rolling or recreate; expected downtime; how deployments are performed step by step" -->
### Rollback Procedure
<!-- field id=smtd.rollback required=yes na=no source=releases hint="How to roll back application, database migrations and configuration; decision criteria; time to roll back" -->
### Post-Deployment Verification
<!-- field id=smtd.post-deploy required=yes na=no source=releases hint="Smoke tests and health checks to run after a deployment and the signals that mean success or failure" -->
### Delivery Performance Metrics
<!-- field id=smtd.dora required=no na=allowed source=releases hint="Deployment frequency, lead time for changes, change failure rate and time to restore" -->
