# Testing Guide - Stripe Checkout Payment Integration

This guide covers how to run all tests for the LandTen Stripe Checkout payment integration.

## 📋 Table of Contents

- [Test Coverage](#test-coverage)
- [Backend Tests](#backend-tests)
- [Frontend Tests](#frontend-tests)
- [Integration Tests](#integration-tests)
- [Test Data](#test-data)
- [Troubleshooting](#troubleshooting)

## 🎯 Test Coverage

The test suite covers three payment flows:

1. **Job Payment** - Landlord → Contractor (job completion)
2. **Rent Payment** - Tenant → Landlord (rent payments)
3. **Platform Fee** - Landlord → Platform (subscription fees)

### What's Tested

**Backend:**
- ✅ API route validation
- ✅ Stripe service methods
- ✅ Error handling
- ✅ Amount conversion (dollars → cents)
- ✅ Customer creation/lookup
- ✅ Metadata handling

**Frontend:**
- ✅ Component rendering
- ✅ Button interactions
- ✅ API calls
- ✅ Loading states
- ✅ Error handling

## 🐍 Backend Tests

### Prerequisites

```bash
cd backend
pip install pytest pytest-cov pytest-mock
```

### Running Backend Tests

```bash
cd backend
pytest tests/ -v
```

## ⚛️ Frontend Tests

### Running Frontend Tests

```bash
cd frontend
npm test
```

## 🔗 Integration Tests

```bash
cd backend
python tests/integration_test.py
```

See full documentation in the file for details.
