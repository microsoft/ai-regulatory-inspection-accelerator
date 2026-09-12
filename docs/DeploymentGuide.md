# Deployment Guide

**Status: Planned.** The Core Platform (`src/platform/`) has not been implemented yet, so there is nothing deployable today. This guide will be filled in once the [Core Platform implementation](../README.md#roadmap) lands.

## What this guide will cover

1. Provisioning the Single Tenant Azure footprint via the Terraform modules in `infra/terraform/` (Azure OpenAI, Azure Document Intelligence, Cosmos DB, Azure AI Search, Storage, Key Vault, Functions, APIM)
2. Configuring environment variables and Managed Identity role assignments (zero-secrets pattern - see [Technical Architecture, Section 11](architecture/TechnicalArchitecture.md#11-azure-reference-architecture))
3. Installing and activating an industry template (starting with `food-safety`)
4. Verifying the deployment with a health check and a sample case submission
5. Tearing down (`terraform destroy`) to avoid ongoing charges

## Today, you can

- Review the [Terraform modules](../infra/terraform/) (currently scaffolding - not yet populated)
- Review the [Technical Architecture](architecture/TechnicalArchitecture.md) for the intended Azure service list and topology
- Track progress on the Core Platform port in [Issues](https://github.com/microsoft/dstoolkit-document-inspection-agent/issues)
