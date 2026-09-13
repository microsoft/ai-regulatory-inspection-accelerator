---
title: ARIA Documentation Index
description: Index of architecture, deployment, customization, and evaluation documentation for ARIA
author: ARIA Engineering
ms.date: 2026-08-24
ms.topic: reference
---

This folder contains supporting documentation for **ARIA - AI Regulatory Inspection Accelerator**, a reusable, Azure-native Solution Accelerator. See the root [README.md](../README.md) for the full solution overview, business scenario, and getting started guide.

---

## Architecture

- [Technical Architecture](architecture/TechnicalArchitecture.md) - capability map, logical/component/agent architecture, token efficiency design, template framework, data and integration architecture, deployment topologies, Azure reference architecture, and key decisions.

## Deployment and operations

- [Enterprise Production Deployment Guide](DeploymentGuide.md) - provisioning and deploying the platform into production Azure environments (Durable Functions, Azure OpenAI, Document Intelligence, Cosmos DB, Key Vault, APIM).
- [Hackathon Demo & Walkthrough Guide](HackathonDemo.md) - quick evaluation guide for the hosted demo UI, sample scenarios, and live vs. synthetic mode switching.
- [Local Development & Testing Setup](LocalDevelopmentSetup.md) - running tests locally (`pytest`), Python virtual environment setup, and local runtime configuration.
- [Troubleshooting & Diagnostics Guide](TroubleshootingSteps.md) - common deployment, APIM policy, quota, and runtime diagnostics.

## Customize

- [Customize: Add a New Industry Template](CustomizeIndustryTemplate.md) - the 14-artifact template contract and how to draft a new industry template today.

## Quality and evaluation

- [Arabic-English Evaluation Standard](ArabicEnglishEvaluation.md) - challenge-set coverage, safety gates, native-speaker review requirements, and authoritative language references.

---

