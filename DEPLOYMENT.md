# Deployment Checklist - Responses API Migration

This document outlines the deployment process for the Responses API migration.

## Overview

**Migration**: Dual-Agent Architecture → OpenAI Responses API
**Date**: December 8, 2025
**Branch**: `claude/assistants-to-responses-migration-01AiwKigtzutWutk9zbHpHpQ`
**Estimated Downtime**: < 5 minutes (service restart only)

---

## Pre-Deployment Checklist

### ✅ 1. OpenAI Dashboard Setup

- [ ] **Create Unified Prompt in OpenAI Dashboard**
  - Go to [https://platform.openai.com/prompts](https://platform.openai.com/prompts)
  - Click "Create prompt"
  - Copy content from `prompts/landten-unified-prompt-v1.md`
  - Paste into prompt editor
  - Save the prompt

- [ ] **Get Prompt ID**
  - Copy the prompt ID (starts with `prompt_`)
  - Format: `prompt_xxxxxxxxxxxxxxxxxxxxx`
  - Keep this handy for environment configuration

- [ ] **Verify OpenAI API Access**
  - Confirm OpenAI API key is valid
  - Check you have access to Responses API (currently in beta)
  - Verify billing is set up

### ✅ 2. Environment Configuration

- [ ] **Set Required Environment Variables**
  ```bash
  # OpenAI Responses API
  export LANDTEN_PROMPT_ID=prompt_xxxxx  # Replace with your prompt ID

  # DynamoDB Table (optional custom name)
  export CONVERSATION_MAPPING_TABLE=landten_conversation_mappings

  # Verify existing OpenAI configuration
  export OPENAI_API_KEY=sk-...  # Should already be set
  ```

- [ ] **Verify `.env` File**
  - Check `backend/.env` has all required variables
  - Compare against `backend/.env.example`

### ✅ 3. Database Setup

- [ ] **Create DynamoDB Table**
  ```bash
  aws dynamodb create-table \
    --table-name landten_conversation_mappings \
    --attribute-definitions AttributeName=channel_id,AttributeType=S \
    --key-schema AttributeName=channel_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
  ```

---

## Deployment Steps

### 🚀 1. Deploy Code

- [ ] **Merge to Master and Deploy**
  ```bash
  git checkout master
  git merge claude/assistants-to-responses-migration-01AiwKigtzutWutk9zbHpHpQ
  git push origin master
  ```

### 🚀 2. Restart Services

- [ ] **Restart Backend**
  ```bash
  sudo systemctl restart landten-backend
  ```

---

## Post-Deployment Validation

- [ ] **Send test message** → verify empathetic response
- [ ] **Report maintenance issue** → verify discovery starts
- [ ] **Answer all questions** → verify incident created
- [ ] **Report second issue** → verify topic switching works
- [ ] **Check conversation state** persists across messages

---

## Rollback Plan

If issues occur:
1. Uncomment old dual-agent code in `ai_webhooks_v3.py` (lines 378-842)
2. Comment out ResponseHandler code (lines 307-377)
3. Restart services
4. Report issues in GitHub
